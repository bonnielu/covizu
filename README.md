# CoVizu: Real-time visualization of SARS-COV-2 genomic diversity

CoVizu is an open source project to develop a public interface to visualize and explore global diversity of SARS-CoV-2 genomes in near real time.

There is a rapidly accumulating number of genome sequences of severe acute 
respiratory syndrome coronavirus 2 (SARS-CoV-2) collected at sites around 
the world, predominantly available through the Global Intiative on Sharing 
All Influenza Data (GISAID) database.
The public release of these genome sequences in near real-time is an 
unprecedented resource for molecular epidemiology and public health.
For example, [nextstrain](http://nextstrain.org) has been at the forefront 
of analyzing and communicating the global distribution of SARS-CoV-2 genomic 
variation.

## Installation

For most users, the results of our analysis are updated every two days and displayed at https://filogeneti.ca/CoVizu.
To run your own local instance of CoVizu, please refer to the installation instructions in the [opendata](https://github.com/PoonLab/covizu/tree/opendata) branch of this repository.


## Visualization concept

To visualize the evolutionary relationships among genomes, CoVizu employs a visual device that we call a "beadplot":

<p align="center">
<img src="doc/beadplot.png" width="500px"/>
</p>

* Each horizontal line segment represents a unique SARS-CoV-2 genomic sequence variant.  The emergence of a single new mutation in an infection is sufficient to establish a new variant.  A given variant may be observed multiple times as identical genome sequences, where `identity' is loosely defined to accommodate genomes with incomplete coverage and ambiguous base calls.  (Following GISAID's definition of a "complete genome", we require a minimum sequence length of 29,000 nt.)
* Each circle represents one or more cases of a variant that were sampled on a given date.  The size (area) of the circle is proportional to the number of sequences.
* Cases are arranged in chronological order from left to right.
* Vertical lines connect variants that are related by a minimum spanning tree, which gives a *rough* approximation of transmission links.  The variant at the bottom terminus of the vertical line is the putative source.  
* The relative location of variants along the vertical axis does not convey any information.  The variants are sorted with respect to the vertical axis such that ancestral variants are always below their "descendant" variants.

**It is not feasible to reconstruct accurate links using only genomic data.**  However, our objective is to identify population-level events like importations into Canada, not to attribute a transmission to a specific source individual.




## Workflow

1. Genome sequences are provisioned by the GISAID database.  All developers have signed the GISAID data access agreement, and sequences are not being re-distributed.

2. Sequences are aligned pairwise against the SARS-COV-2 reference genome using the short read mapper [minimap2](https://github.com/lh3/minimap2) and all genetic differences from the reference are extracted as "features", excluding [problematic sites](https://github.com/W-L/ProblematicSites_SARS-CoV2).  Genomes are filtered for <1% uncalled bases, divergence consistent with a molecular clock.  The end result is a compact representation of each genome as a feature set.

3. A single representative genome is selected for each [PANGO](https://cov-lineages.org/) lineage by selecting the earliest available genome from the curated list of genomes comprising the [PANGO lineage designations](https://github.com/cov-lineages/pango-designation).  A time-scaled tree is reconstructed the representative genomes using a combination of [fasttree2](http://www.microbesonline.org/fasttree/) and [TreeTime](https://github.com/neherlab/treetime).

4. We calculate the [symmetric difference](https://en.wikipedia.org/wiki/Symmetric_difference) between every pair of genomes in a lineage, and generate 100 replicate bootstrap samples from the lineage feature set union.  We apply the resulting samples to the symmetric differences to generate reweighted distance matrices.  Each distance matrix is used to reconstruct a [neighbor-joining](https://en.wikipedia.org/wiki/Neighbor_joining) tree using [RapidNJ](https://birc.au.dk/software/rapidnj/).

5. For each lineage, a consensus tree is calculated from the set of bootstrap trees and converted into a beadplot.


## Acknowledgements
The development and validation of these scripts was made possible by the labs who have generated and contributed SARS-COV-2 genomic sequence data that is curated and published by [GISAID](https://www.gisaid.org/).  We sincerely thank these labs for making this information available to the public and open science.
