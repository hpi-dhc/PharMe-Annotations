# PharMe Annotations

This repository holds relevant pharmacogenomic annotations from external sources
other than CPIC to be accessed the PharMe's Annotation Interface (Anni).

Anni reads each of the files in [`annotations/`](./annotations/) and adds their
contents to its database when its initialization endpoint is triggered. The file
name (with `.json` omitted) will be displayed as the source in Anni and the App.

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

### Resolve phenotypes

Uses the CPIC API to copy files from `unresolved-annotations/` to `annotations/`
and duplicate phenotype entries per `lookupkey`.

⚠️ _Mind that Anni fetches data only from `annotations/`, if you make changes
only in `unresolved-annotations/` without running the script, they will not
be adopted. (And yes, this could be automated with a workflow, but I currently
don't have time for this.)_

### Crawl FDA Associations

Uses the FDA
[Table of Pharmacogenetic Associations](https://www.fda.gov/medical-devices/precision-medicine/table-pharmacogenetic-associations)
to create CPIC-style annotations in `unresolved-annotations/`.

Uses the CPIC API to skip drugs already included in CPIC and the Rx API to
get RxCUIs.

⚠️ _Potentially confusing behavior_: when multiple genes are stated in the table
with "and/or", combinations with "Indeterminate" phenotype will be created.

🚨 **Known problem**: if associations for one drug and multiple genes are not
contained in one row, one guideline will be created per gene instead of having
combined guidelines. Need to clarify how to deal with these, as we want to show
users one combined guideline. Currently ignoring these cases, could add later
manually.
