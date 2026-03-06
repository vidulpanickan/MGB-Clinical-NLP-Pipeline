# Clinical NLP Pipeline Guide

This documentation provides a pipeline for running **NILE** for clinical entity extraction.

---

## Pipeline Workflow

### STEP 1: Data Source Identification
The NILE framework supports multiple input architectures. Prior to execution, confirm the source and format of your clinical data. 

**General Supported Formats:**
* **Relational Database:** Direct connection to SQL.
* **Standard Flat File:** CSV format containing a single clinical note per row.
* **RPDR Format:** Standardized note format utilized by the MGB Research Patient Data Registry.

**Active Project Configurations:**
* **BIOBANK 2025:**
    * **Format:** RPDR note format
    * **File Path:** `/data/vbio-methodsdev/SHARE/BIOBANK/2025/Raw_Data/Biobank_RPDR_notes_2025`
    * **Structure:** Split into 17 folders
* **RAPROD5:**
    * **Format:** Standard Flat File (CSV) OR Relational Database
    * **File Path (CSV):** `/data/vbio-methodsdev/SHARE/RAPROD5/raw_data/notes_batches_ready4nile`
    * **Structure:** Split into 77 individual CSV files
    * **Database Source:** Notes are also available directly on the RAProd5 database.

### STEP 2: Population Subsetting
Determine if the analysis requires the complete patient cohort or a specific sub-population. 
* **Complete Cohort:** Proceed directly to Step 3.
* **Sub-population Extraction:** For subsetting notes based on specific clinical or demographic criteria, utilize the extraction tools available here:
    * [MGB-Research-Data-Pipelines/EXTRACT](https://github.com/vidulpanickan/MGB-Research-Data-Pipelines/tree/main/EXTRACT)

### STEP 3: NILE Run
Execute the core Natural Language Processing engine to perform entity extraction on the clinical text.
* Detailed execution parameters and model configurations are located in the primary NILE repository:
    * [MGB-Research-Data-Pipelines/NILE](https://github.com/vidulpanickan/MGB-Research-Data-Pipelines/tree/main/NILE)

### STEP 4: Post-processing Output
Following the generation of raw NILE results, perform data validation and longitudinal aggregation.
* **Temporal Analysis:** Generate daily and monthly frequency counts on raw outputs.
* **Data Roll-up:** Aggregate CUIs to Parent-level CUIs using the SNOMED CT Hierarchy.
* Post-processing scripts are available at:
    * [MGB-Research-Data-Pipelines/POSTPROCESS](https://github.com/vidulpanickan/MGB-Research-Data-Pipelines/tree/main/POSTPROCESS)

---

## Repository Structure Overview

| Component | Function | Resource Link |
| :--- | :--- | :--- |
| **Extraction** | Population subsetting and data filtering | [/EXTRACT](https://github.com/vidulpanickan/MGB-Research-Data-Pipelines/tree/main/EXTRACT) |
| **NLP Engine** | Core NILE extraction logic | [/NILE](https://github.com/vidulpanickan/MGB-Research-Data-Pipelines/tree/main/NILE) |
| **Post-processing** | Validation, temporal counts, and roll-ups | [/POSTPROCESS](https://github.com/vidulpanickan/MGB-Research-Data-Pipelines/tree/main/POSTPROCESS) |
