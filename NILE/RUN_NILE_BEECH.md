# Running the NILE Database Processor (Shared Server)

Processes clinical notes stored in a SQL Server database through NILE and writes
pipe-delimited output files (`patient_id|doc_id|date|note_type|code_certainty`).

This server is already set up. **You only need to run it** — no compiling, no
downloading drivers. Follow the four steps below.

---

## Before you start

- **Java 64-bit must be on your PATH.** Check with `java -version` — the output
  must say **64-Bit** somewhere. (A 32-bit JVM cannot load the auth DLL and will
  fail with a misleading error — see Troubleshooting.)
- **Your Windows account needs access to the target database.** This tool uses
  Windows / integrated authentication, which means it connects to SQL Server *as
  the Windows user who runs it* — i.e. as you. If your account can't reach the
  database, ask whoever administers the SQL Server to grant it.
- Work inside the shared project folder (the "project root"):
  `D:\NLP_tools\LATEST_NILE\refactored-nile-processing-main\refactored-nile-processing-main`

## Already configured on this server — do not change

- NILE is compiled (the `NILE\*.class` files are present).
- The SQL Server auth DLL is in place: `NILE\sqljdbc_auth\mssql-jdbc_auth-12.4.3.x64.dll`.
- The driver jars are in `NILE\lib`. Only **one** `mssql-jdbc` jar should be active
  (`mssql-jdbc-12.4.3.jre11.jar`); the DLL version must match the jar version, so
  don't add a second `mssql-jdbc` jar to `NILE\lib` (that breaks auth — see
  Troubleshooting).

---

## Step 1 — Open Command Prompt at the project root

```bat
cd /d "D:\NLP_tools\LATEST_NILE\refactored-nile-processing-main\refactored-nile-processing-main"
```

All commands below use paths relative to this folder, so you must run them from here.

## Step 2 — Make your own properties file

The processor reads every setting from a properties file. To avoid colliding with
other people editing the same file, **copy it to your own version** and edit that:

```bat
copy NILE\NLPproperties.txt NILE\NLPproperties_yourname.txt
notepad NILE\NLPproperties_yourname.txt
```

Fill in / check these fields:

| Field | What to set |
|---|---|
| `server` | SQL Server hostname / instance |
| `dbname` | Database name |
| `tablename` | Table containing the clinical notes |
| `patientIDcol`, `docIDcol`, `datecolumn`, `notecolumn`, `notetype` | Column names in that table |
| `patstart`, `patend`, `patincrement` | Patient ID range and batch size (e.g. 1 / 10000 / 10000 = one file with patients 1–10000) |
| `notelengthlimit` | Notes shorter than this many characters are skipped |
| `outputfolder` | **Your own** full output path, e.g. `D:\...\output\yourname`. Don't point at a shared folder or you'll overwrite other people's results. |
| `user`, `password` | **Leave blank** to log in with your Windows account (integrated auth). |

## Step 3 — Run

One line, from the project root. Swap in your own properties filename:

```bat
java "-Djava.library.path=NILE\sqljdbc_auth" -cp ".;NILE\lib\*" NILE.NILEDatabaseProcessor "NILE\NLPproperties_yourname.txt"
```

Notes:
- `-Djava.library.path=NILE\sqljdbc_auth` points at the **folder** holding the DLL
  (not the DLL file). This is how Java finds the Windows-auth library.
- `NILE.NILEDatabaseProcessor` keeps the `NILE.` prefix — that's the package name.
- A successful run prints something like `NILE NLP processor initialized
  successfully` followed by per-batch progress.

## Step 4 — Check your output

Output files land in the `outputfolder` you set, named `batch_{patstart}_{patend}.csv`,
pipe-delimited. Spot-check one:

```bat
type D:\path\to\your\outputfolder\batch_1_10000.csv
```

---

## Troubleshooting

These are the exact errors seen during setup and what each one means.

**`This driver is not configured for integrated authentication.`**
The driver tried Windows auth but couldn't load the native DLL. Two causes:
1. *Version mismatch.* The driver looks for an auth DLL named after its **own**
   version. The `mssql-jdbc` jar on the classpath and the
   `mssql-jdbc_auth-<version>.x64.dll` must be the same version. If someone added a
   second `mssql-jdbc` jar to `NILE\lib` (e.g. both 12.4.0 and 12.4.3), the wildcard
   `NILE\lib\*` may load the one with no matching DLL. Fix: keep only the matching
   jar in `lib` (move the other to `*.bak`), or copy the DLL to the other version's
   name so both exist.
2. *32-bit Java.* An x86 JVM can't load the x64 DLL and throws this same message.
   Run `java -version`; it must say 64-Bit. Install / switch to a 64-bit JDK.

**`error reading ...jar; zip END header not found`** (only when recompiling)
A jar in `NILE\lib` is corrupt or was downloaded incompletely (often the large
Hadoop jars used by the Parquet processor). The wildcard tries to read every jar.
Fix: move the bad jar aside — `move NILE\lib\<badjar> NILE\lib\<badjar>.bad` — or
re-download a clean copy. The database processor doesn't need the Hadoop jars.

**`package ... does not exist` / `cannot find symbol`** (only when recompiling)
The classpath isn't pointing at the jars. From the project root the jars are under
`NILE\lib\...`, not `lib\...`. javac silently ignores classpath entries that don't
exist, so a wrong path shows up as "package does not exist."

**`Could not find or load main class`**
The `NILE.` package prefix was dropped. Run it as `NILE.NILEDatabaseProcessor`.

**A TLS / server-certificate error**
Modern drivers encrypt by default; if the SQL Server uses a self-signed cert the
connection string needs `encrypt=true;trustServerCertificate=true`. This is set in
the processor's connection logic, not the properties file — flag it to whoever
maintains the code.

---

## Quick reference (copy-paste)

```bat
cd /d "D:\NLP_tools\LATEST_NILE\refactored-nile-processing-main\refactored-nile-processing-main"
copy NILE\NLPproperties.txt NILE\NLPproperties_yourname.txt
notepad NILE\NLPproperties_yourname.txt
java "-Djava.library.path=NILE\sqljdbc_auth" -cp ".;NILE\lib\*" NILE.NILEDatabaseProcessor "NILE\NLPproperties_yourname.txt"
```
