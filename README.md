# PharMe Annotations

This repository holds relevant pharmacogenomic annotations from external sources
other than CPIC to be accessed the PharMe's Annotation Interface (Anni).

Anni reads each of the files in [`annotations/`](./annotations/) and adds their
contents to its database when its initialization endpoint is triggered. The file
name (with `.json` omitted) will be displayed as the source in Anni and the App.

## Data format

All data is kept as JSON in CPIC's `recommendation` format, as a list of items
abiding by the following structure.

```typescript
{
    "id": Integer,
    "version": Integer,
    "drugid": String,
    "drug": {
        "name": String
    },
    "lookupkey": {
        [gene: String]: String
    },
    "phenotype": {
        [gene: String]: String
    },
    "guideline": {
        "name": String,
        "url": String
    },
    "implications": {
        [gene: String]: String
    },
    "drugrecommendation": String,
    "comment": String?
}
```

A large example of such a list can be found by using CPIC's API as follows.

```plain
https://api.cpicpgx.org/v1/recommendation?select=id,drugid,version,drug(name),lookupkey,phenotypes,guideline(name,url),implications,drugrecommendation,comments
```

## Phenotype identification

Note that these annotations use a CPIC `lookupkey` for phenotype identification
and that the same phenotype may be a result of multiple `lookupkey`s. In these
cases, the given entry should be duplicated for all matching `lookupkey`s.

In the annotation interface, 

To check which `lookupkey`s map to a given phenotype, use the following API
endpoint of CPIC

```plain
https://api.cpicpgx.org/v1/diplotype?genesymbol=eq.<GENE_SYMBOL>&generesult=eq.<GENE_RESULT>&select=lookupkey,generesult
```

by replacing `GENE_SYMBOL` and `GENE_RESULT` with the desired
phenotype information, e.g. `CYP2D6` and `Poor Metabolizer` respectively.
