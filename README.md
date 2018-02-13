# gitDIGR Toolset


# Description
gitDIGR (for **git** **D**evelopment **I**nformation **G**rabber for **R**epositories) is a toolset for collecting, scraping, and analyzing the changelog information observable in a set of git repositores. The gitDIGR framework consists of Python scripts that are designed to assist with tasks oriented toward mining git repositories to obtain information and insights on repository commit activity and events.


## collector.py

List or batch-retrieve the repositories associated with a particular GitHub user account.

| argument | type | description |
|----------|------|-------------|
| \-s, \-\-sources | string | semi\-colon\-separated list of repository URLs, or an input text file containing the same |
| \-\-host | string | HTTPS GitHub hostname |
| \-p, \-\-password | flag | prompt for GitHub username and password |
| \-t, \-\-token | flag | prompt for GitHub access token |
| \-u, \-\-username | string | process repositories associated with the specified GitHub user |
| \-q, \-\-query | string | process only repositories containing particular tokens in their URL text |
| \-\-until | string | process only repositories modified before a particular date |
| \-\-since | string | process only repositories created after a particular date |
| \-r, \-\-retrieve | flag | clone repositories |
| \-a, \-\-anonymize | flag | apply anonymization to cloned repository paths |
| \-b, \-\-bare | flag | opt for bare repositories when cloning |
| \-d, \-\-directory | string | runtime working directory for cloned repositores |
| \-o, \-\-outfile | string | output file containing semi\-colon\-separated list of cloned repository paths relative to local working environment |

### Example Usage

**1. List all (accessible) repository HTTPS URLs associated with particular GitHub user:**
```
$ python collector.py --host https://github.com -u {user} -p
```

**2. Retrieve an anonymized, bare repository:**
```
$ python collector.py -s https://{github.host.name}/{repo_owner}/{repo_name} -r -a -b
```

**3. Retrieve some set of repositories created after Jan. 01, 1970:**
```
$ python collector.py -s {repo_urls_list_file} -r --since 1970-01-01
```



## scraper.py

Obtain commit history information for a set of git repositories in tabular format and export the resulting records to a data store.

| argument | type | description |
|----------|------|-------------|
| \-s, \-\-sources | string | semi\-colon\-separated list of repository paths \(relative to local working environment\), or an input text file containing the same |
| \-a, \-\-anonymize | flag | apply anonymization to resulting repository commit records |
| \-\-paths\-in\-repo | string | comma-separated list of paths to process relative to all repositories |
| \-\-files\-in\-repo | string | comma-separated list of files to process relative to all repositories |
| \-\-data\-store | string | specify data store object |
| \-\-until | string | consider only repository commits performed before a particular date |
| \-\-since | string | consider only repository commits performed after a particular date |

### Example Usage

**1. Export repository commit information to some data store:**
```
$ python scraper.py -s {relative/path/to/reposotory} --data-store {ds_object}
```

**2. Export repository commit information concerning a specific path and a specific file:**
```
$ python scraper.py -s {relative/path/to/reposotory}{?}{path=path_1}{&}{file=file_1} --data-store {ds_object}
```

**3. Export anonymized repository commit information for any commits performed after Jan. 01, 1970:**
```
$ python scraper.py -s {relative/path/to/reposotory} -a --data-store {ds_object} --since 1970-01-01
```

**4. Export repository commit information concerning particular paths for some set of repositories:**
```
$ python scraper.py -s {relative/path/to/reposotory} --paths-in-repo {path_1, path_2,..., path_n} --data-store {ds_object}
```



## analyzer.py

Generate statistical information based on a set of repository commit records. This information corresponds to a set of repository metrics \(based on attributes observable in revision history\), and are presented as frequency distribution tables \(spreadsheets files\) and distribution graphics \(HTML file\).

| argument | type | description |
|----------|------|-------------|
| \-\-data\-store | string | specify data store object |

### Example Usage

**1. Generate repository statistics for a set of commit records accessible in some data store:**
```
$ python analyzer.py --data-store {ds_object}
```



# Required Python Modules
- argparse
- bokeh
- collections
- datetime
- getpass
- io
- numpy
- os
- pandas
- re
- requests
- subprocess
- sys
- textwrap
- time
- urlparse
