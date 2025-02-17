import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="covizu",
    version="0.3",
    description="Visualization of SARS-CoV-2 diversity",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Art Poon, Emmanuel Wong, Kaitlyn Wade, Molly Liu, Roux-Cil Ferreira, "
           "Laura Munoz Baena, Abayomi Olabode",
    url="https://github.com/PoonLab/covizu",
    packages=setuptools.find_packages(),
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_data={'covizu': [
        'data/problematic_sites_sarsCov2.vcf',
        'data/lineages.csv',
        'data/NC_045512.fa'
    ]}
)
