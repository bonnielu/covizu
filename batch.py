import argparse
import os
import sys
import json
from datetime import datetime

import covizu
from covizu.utils import gisaid_utils
from covizu.utils.progress_utils import Callback
from covizu.utils.batch_utils import *
from covizu.utils.seq_utils import SC2Locator
from tempfile import NamedTemporaryFile


def parse_args():
    parser = argparse.ArgumentParser(description="CoVizu analysis pipeline automation")

    parser.add_argument('--url', type=str, default=os.environ.get("GISAID_URL", None),
                        help="URL to download provision file, defaults to environment variable.")
    parser.add_argument('--user', type=str, default=os.environ.get("GISAID_USER", None),
                        help="GISAID username, defaults to environment variable.")
    parser.add_argument('--password', type=str, default=os.environ.get("GISAID_PSWD", None),
                        help="GISAID password, defaults to environment variable.")

    parser.add_argument("--infile", type=str, default=None,
                        help="input, path to xz-compressed JSON; if not specified, "
                             "download xz file from GISAID provision feed.")
    parser.add_argument("--outdir", type=str, default='data/',
                        help="option, path to write output files")

    parser.add_argument('--minlen', type=int, default=29000, help='option, minimum genome length (nt)')
    parser.add_argument('--mindate', type=str, default='2019-12-01', 
                        help='option, earliest possible sample collection date (ISO format, default '
                              '2019-12-01')
    parser.add_argument('--poisson-cutoff', type=float, default=0.001,
                        help='option, filtering outlying genomes whose distance exceeds the upper '
                             'quantile of Poisson distribution (molecular clock).  Default 0.001 '
                             'corresponds to 99.9%% cutoff.')
   
    parser.add_argument('--batchsize', type=int, default=2000,
                        help='option, number of records to batch process with minimap2')
    parser.add_argument('--max-variants', type=int, default=5000,
                        help='option, limit number of variants per lineage (default 5000)')

    parser.add_argument("--ref", type=str,
                        default=os.path.join(covizu.__path__[0], "data/NC_045512.fa"),
                        help="option, path to FASTA file with reference genome")
    parser.add_argument('--mmbin', type=str, default='minimap2',
                        help="option, path to minimap2 binary executable")
    parser.add_argument('-mmt', "--mmthreads", type=int, default=16,
                        help="option, number of threads for minimap2.")

    parser.add_argument('--misstol', type=int, default=300,
                        help="option, maximum tolerated number of missing bases per "
                             "genome (default 300).")
    parser.add_argument("--vcf", type=str,
                        default=os.path.join(covizu.__path__[0], "data/problematic_sites_sarsCov2.vcf"),
                        help="Path to VCF file of problematic sites in SARS-COV-2 genome. "
                             "Source: https://github.com/W-L/ProblematicSites_SARS-CoV2")

    parser.add_argument('--ft2bin', default='fasttree2',
                        help='option, path to fasttree2 binary executable')

    parser.add_argument('--lineages', type=str,
                        default=os.path.join(covizu.__path__[0], "data/lineages.csv"),
                        help="optional, path to CSV file containing Pango lineage designations.")
    parser.add_argument('--ttbin', default='treetime',
                        help='option, path to treetime binary executable')
    parser.add_argument('--clock', type=float, default=8e-4,
                        help='option, specify molecular clock rate for '
                             'constraining Treetime analysis (default 8e-4).')
    parser.add_argument('--earliest', action='store_true', 
                        help='option, use earliest sample per lineage for time-scaled '
                             'tree; otherwise defaults to most recent samples.')

    parser.add_argument('--datetol', type=float, default=0.1,
                        help='option, exclude tips from time-scaled tree '
                             'with high discordance between estimated and '
                             'known sample collection dates (year units,'
                             'default: 0.1)')

    parser.add_argument('--binpath', type=str, default='rapidnj',
                        help='option, path to RapidNJ binary executable')
    parser.add_argument('--mincount', type=int, default=5000,
                        help='option, minimum number of variants in lineage '
                             'above which MPI processing will be used.')
    parser.add_argument('--machine_file', type=str, default='mfile',
                        help='option, path to machine file for MPI.')
    parser.add_argument("-n", "--nboot", type=int, default=100,
                        help="Number of bootstrap samples, default 100.")

    parser.add_argument("--boot-cutoff", type=float, default=0.5,
                        help="Bootstrap cutoff for consensus tree (default 0.5). "
                             "Only used if --cons is specified.")

    parser.add_argument("--dry-run", action="store_true",
                        help="Do not upload output files to webserver.")

    return parser.parse_args()


def process_feed(args, callback=None):
    """ Process feed data """
    if callback:
        callback("Processing GISAID feed data")
    loader = gisaid_utils.load_gisaid(args.infile, minlen=args.minlen, mindate=args.mindate)
    batcher = gisaid_utils.batch_fasta(loader, size=args.batchsize)
    aligned = gisaid_utils.extract_features(batcher, ref_file=args.ref, binpath=args.mmbin,
                                            nthread=args.mmthreads, minlen=args.minlen)
    filtered = gisaid_utils.filter_problematic(aligned, vcf_file=args.vcf, cutoff=args.poisson_cutoff,
                                               callback=callback)
    return gisaid_utils.sort_by_lineage(filtered, callback=callback)


if __name__ == "__main__":
    args = parse_args()
    cb = Callback()

    # check that user has loaded openmpi module
    try:
        subprocess.check_call(['mpirun', '-np', '2', 'ls'], stdout=subprocess.DEVNULL)
    except FileNotFoundError:
        cb.callback("mpirun not loaded - run `module load openmpi/gnu`", level='ERROR')
        sys.exit()

    # download xz file if not specified by user
    if args.infile is None:
        cb.callback("No input specified, downloading data from GISAID feed...")
        args.infile = gisaid_utils.download_feed(args.url, args.user, args.password)

    # filter data, align genomes, extract features, sort by lineage
    by_lineage = process_feed(args, cb.callback)

    # reconstruct time-scaled tree relating lineages
    timetree, residuals = build_timetree(by_lineage, args, cb.callback)
    timestamp = datetime.now().isoformat().split('.')[0]
    nwk_file = os.path.join(args.outdir, 'timetree.{}.nwk'.format(timestamp))
    with open(nwk_file, 'w') as handle:
        Phylo.write(timetree, file=handle, format='newick')

    # clustering analysis of lineages
    result = make_beadplots(by_lineage, args, cb.callback, t0=cb.t0.timestamp())
    clust_file = os.path.join(args.outdir, 'clusters.{}.json'.format(timestamp))
    with open(clust_file, 'w') as handle:
        json.dump(result, fp=handle)

    # get mutation info
    locator = SC2Locator()
    mutations = {}
    for lineage, features in get_mutations(by_lineage).items():
        annots = [locator.parse_mutation(f) for f in features]
        mutations.update({lineage: [a for a in annots if a is not None]})

    # write data stats
    dbstat_file = os.path.join(args.outdir, 'dbstats.{}.json'.format(timestamp))
    with open(dbstat_file, 'w') as handle:
        nseqs = sum([len(rows) for rows in by_lineage.values()])
        val = {
            'lastupdate': timestamp.split('T')[0],
            'noseqs': nseqs,
            'lineages': {}
        }
        for lineage, samples in by_lineage.items():
            ndiffs = [len(x['diffs']) for x in samples]
            val['lineages'][lineage] = {
                'nsamples': len(samples),
                'lastcoldate': max(x['covv_collection_date'] for x in samples),
                'residual': residuals[lineage],
                'max_ndiffs': max(ndiffs),
                'mean_ndiffs': sum(ndiffs)/len(ndiffs),
                'mutations': mutations[lineage]
            }
        json.dump(val, handle)

    # upload output files to webserver, requires SSH key credentials
    if not args.dry_run:
        server_root = 'filogeneti.ca:/var/www/html/covizu/data'
        subprocess.check_call(['scp', nwk_file, '{}/timetree.nwk'.format(server_root)])
        subprocess.check_call(['scp', clust_file, '{}/clusters.json'.format(server_root)])
        subprocess.check_call(['scp', dbstat_file, '{}/dbstats.json'.format(server_root)])

        # upload files to EpiCoV server
        server_epicov = 'filogeneti.ca:/var/www/html/epicov/data'
        subprocess.check_call(['scp', nwk_file, '{}/timetree.nwk'.format(server_epicov)])
        subprocess.check_call(['scp', dbstat_file, '{}/dbstats.json'.format(server_epicov)])

        # modify clusters JSON
        epifile = open(clust_file, 'r')
        epicov_data = gisaid_utils.convert_json(epifile, args.infile)
        fp = NamedTemporaryFile('w', delete=False)
        json.dump(epicov_data, fp=fp)  # serialize to temp file
        fp.close()
        subprocess.check_call(['scp', fp.name, '{}/clusters.json'.format(server_epicov)])

    cb.callback("All done!")
