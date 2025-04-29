# PharMe Annotations

This repository holds relevant pharmacogenomic annotations from external sources
other than available through the CPIC API to be accessed the PharMe's Annotation
Interface (Anni).

Anni reads each of the files in [`annotations/`](./annotations/) and adds their
contents to its database when its initialization endpoint is triggered. The file
name (with `.json` omitted) will be displayed as the source in Anni and the App.

_Please note: the term "annotations" is misleading here, as the actual annotation_
_will be created in Anni. The content here could rather be referred to as_
_"additional medication / guideline data"._

## Data format

All data in `annotations/` is kept as JSON in CPIC's `recommendation` format,
as a list of items abiding by the following structure:

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
    "phenotypes": {
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

A large example of such a list can be found by using CPIC's API as follow:

```plain
https://api.cpicpgx.org/v1/recommendation?select=id,drugid,version,drug(name),lookupkey,phenotypes,guideline(name,url),implications,drugrecommendation,comments
```

Note that these annotations use a CPIC `lookupkey` for phenotype identification
and that the same phenotype may be a result of multiple `lookupkey`s. In these
cases, the given entry should be duplicated for all matching `lookupkey`s (also
 [see below](#scripts) for automation of this step).

## Scripts

Helpers to automate tiresome manual work:

* Have 🐍 Python 3 and pip installed (would recommend to use virtual
  environment)
* Install requirements `pip install -r scripts/requirements.txt`
* Run script `python scripts/<SCRIPT_NAME>`

### Resolve annotations

Uses the CPIC API to copy files from `unresolved-annotations/` to `annotations/`
and duplicate phenotype entries per `lookupkey`.

The fields `id` and `version` do not need to given, if missing both will be set
to `1`.

⚠️ _Mind that Anni fetches data only from `annotations/`, if you make changes
only in `unresolved-annotations/` without running the script, they will not
be adopted. (And yes, this could be automated with a workflow, but I currently
don't have time for this.)_

The file `additional_drugs.json` defines drugs without guidelines
that are needed in PharMe, e.g., for drug-drug interactions. Empty annotations
will be created to comply with the `CpicRecommendation` in Anni.

RxCUIs for all manual additions will be added using the Rx API.

For FDA guidelines, recommendations and implications are given as one text;
thus, a standard text that refers to the implication text is added as a
recommendation when resolving.

Manual additions to CPIC guidelines – for medications that explicitly have no
recommendations or recommendations that cannot be processed in PharMe – can be
made by adding to the `recommendationless_CPIC.json`.
In the app, the standard "more data is needed" message will be shown, however,
in contrast to additional drugs an empty recommendation **with a source URL**
will be created.
Either phenotypes and implications can be given or a list of genes that will be
used to create "All" phenotypes and empty implications.

Manual additions to the crawled FDA content (e.g., for guidelines with multiple
rows) can be made by adding to the `manual_FDA.json` file.

### Crawl FDA Associations

Uses the FDA
[Table of Pharmacogenetic Associations](https://www.fda.gov/medical-devices/precision-medicine/table-pharmacogenetic-associations)
to create CPIC-style annotations in `unresolved-annotations/`.

Uses the CPIC API to skip drugs already included in CPIC and the Rx API to
get RxCUIs.

⚠️ _Potentially confusing behavior_: when multiple genes are stated in the table
with "and/or", combinations with "Any not handled in guideline" phenotype will
be created.

🚨 **Known problem**: if associations for one drug and multiple genes are not
contained in one row, one guideline will be created per gene instead of having
combined guidelines. Need to clarify how to deal with these, as we want to show
users one combined guideline. Currently ignoring these cases, could add later
manually.

### Special Phenotypes

In these scrips the "All" phenotype (guidelines without recommendations) and
the "Any not handled in guideline" phenotype (for FDA guidelines) are
introduced.

The lookupkey for "All" is `*`, for "Any not handled in guideline" `~`
(these are used to match user's genotypes to guidelines in the app, next to CPIC
lookups).

## Licenses

* The FDA content is "in the public domain and may be republished, reprinted and
  otherwise used freely by anyone without the need to obtain permission from FDA"
  (see [website policies](https://www.fda.gov/about-fda/about-website/website-policies#linking))
* The CPIC content included from cpicpgx.org (level C guidelines) is is available
  free of restriction under the CC0 1.0 Universal (CC0 1.0) Public Domain Dedication
  (see [Licensing and terms of use](https://cpicpgx.org/license/))
