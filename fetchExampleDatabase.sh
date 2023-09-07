#/bin/sh

mkdir -p swgts-backend/input/databases

cp example_data/EPI_ISL_402124.fasta.gz swgts-backend/input/databases/combinedHumanCovid.fa.gz
curl https://s3-us-west-2.amazonaws.com/human-pangenomics/T2T/CHM13/assemblies/analysis_set/chm13v2.0.fa.gz >> input/databases/combinedHumanCovid.fa.gz
minimap2 -d swgts-backend/input/databases/combinedHumanCovid.mmi swgts-backend/input/databases/combinedHumanCovid.fa.gz
