#!/usr/bin/python


import argparse; # Script arguments.
import datetime; # Datetime handling.
import io; # File writing.
import modules.shared as sh;
import os; # File system handling.
import pandas; # DataFrame handling.
import re; # Regular expressions.
import subprocess; # Git commands.
import sys; # Script termination.
import urlparse; # URL parsing.


# Global variables.

args = ''; # For script arguments object.

repo_owner = '';
repo_name = '';
path_in_repo = '';
path_to_repo = '';

include_paths = list(); # Repo paths to process.
exclude_paths = list(); # Repo paths to ignore.
include_files = list(); # Repo files to process.
exclude_files = list(); # Repo files to ignore.


# Process script arguments.
def process_args():
    
    argparser = argparse.ArgumentParser();
    
    argparser.add_argument('-s','--sources', help="semi-colon-separated list of repo URIs (i.e., URL, local path or input file)", type=str);
    argparser.add_argument('--paths-in-repo', help="comma-separated list of paths in repos to process", type=str);
    argparser.add_argument('--files-in-repo', help="comma-separated list of files in repos to process", type=str);
    argparser.add_argument('--data-store', help="output data store", type=str);
    argparser.add_argument('--since', help="scrape only commits after a specific date", type=str);
    argparser.add_argument('--until', help="scrape only commits before a specific date", type=str);
    argparser.add_argument('-a','--anonymize', help="anonymize repo info in data store", action="store_true");
    
    return argparser.parse_args();


# Check script arguments.
def check_args():
    
    print("Checking script arguments...");
    
    # Repo sources (URIs and corresponding paths).
    args.sources = sh.verify_repo_sources(args.sources, False, True);
    if (not args.sources):
        print("Must provide at least one valid repository URI.");
        sys.exit();
    
    # Output file.
    if (args.data_store):
        data_store = args.data_store;
        if (sh.verify_outfile(data_store)): # If data store is okay to write...
            if (os.path.exists(data_store)): # If data store already exists...
                ds_df = sh.load_commits_data_store(data_store);
                if (ds_df is not None): # If formatting is as expected...
                    args.data_store = os.path.abspath(data_store);
                else:
                    print("Malformed data store \'" + args.data_store + "\'.");
                    sys.exit();
        else:
            sys.exit();
    else: # Default output filename...
        args.data_store = 'scraper-data-store_' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S%f')[:-3];
    
    # Paths in repo.
    args.paths_in_repo = sh.verify_paths_in_repo(args.paths_in_repo);
    
    # Filenames in repo.
    args.files_in_repo = sh.verify_considered_files(args.files_in_repo);
    
    # 'Since' date.
    args.since = sh.verify_since_str(args.since);
    
    # 'Until' date.
    args.until = sh.verify_until_str(args.until);


# Print script argument configurations.
def echo_args():
    
    arg_paths_in_repo = ", ".join(["\'" + p + "\'" for p in args.paths_in_repo]) if (args.paths_in_repo) else "\'.\'";
    arg_files_in_repo = ', '.join(["\'" + f + "\'" for f in args.files_in_repo]) if (args.files_in_repo) else "\'*\'";
    
    print("ALL_REPOS_PATHS: " + str(arg_paths_in_repo));
    print("ALL_REPOS_FILES: " + str(arg_files_in_repo));
    print("SINCE: " + str(args.since));
    print("UNTIL: " + str(args.until));


# Extract repo owner and name from remote origin URL.
def extract_repo_owner_and_name(remote_origin_url):
    
    repo_owner = '';
    repo_name = '';
    
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(remote_origin_url);
    
    if (not scheme):
        path = remote_origin_url.split(':')[1];
    
    repo_owner = os.path.basename(os.path.abspath(os.path.join(path, os.pardir))); # Get name of parent dir in path.
    repo_name = os.path.basename(path);
    
    if (repo_name.endswith('.git')):
        repo_name = repo_name[:-4]; # Remove the '.git' from repo name.
    
    return repo_owner, repo_name;


# Parse information on files affected in a single commit.
def get_commit_filenames(files_str):
    
    filenames_regex = r'\s+(.*)\s+\|\s+[a-zA-Z0-9]+';
    
    filenames = re.findall(filenames_regex, files_str);
    
    for i in range(0, len(filenames)):
        filenames[i] = filenames[i].rstrip(); # Prune leading/trailing spaces from filename str.
    
    return filenames;#(filenames, num_files_changed, num_insertions, num_deletions);


# Get info on line change insertions, deletions and modifications.
def get_changed_lines_info(file_diff):
    
    num_lines_inserted = 0;
    num_lines_deleted = 0;
    num_lines_modified = 0;
    
    addition_regex = r'\{\+.*?\+\}';
    removal_regex = r'\[-.*?-\]';
    
    for line in file_diff:
        
        additions = re.findall(addition_regex, line);
        removals = re.findall(removal_regex, line);
        
        if (additions and not removals):
            if (line.startswith('{+') and line.endswith('+}')):
                if (len(additions) > 1):
                    num_lines_modified = num_lines_modified + 1;
                else:
                    num_lines_inserted = num_lines_inserted + 1;
            else:
                num_lines_modified = num_lines_modified + 1;
        elif (removals and not additions):
            if (line.startswith('[-') and line.endswith('-]')):
                if (len(removals) > 1):
                    num_lines_modified = num_lines_modified + 1;
                else:
                    num_lines_deleted = num_lines_deleted + 1;
            else:
                num_lines_modified = num_lines_modified + 1;
        elif (additions and removals):
            num_lines_modified = num_lines_modified + 1;
    
    return (num_lines_inserted, num_lines_deleted, num_lines_modified);


# Parse info from a single commit's log.
def get_git_show_str(commit_hash):
    
    global path_to_repo;
    
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    wt = '--work-tree=\'' + path_to_repo + '\'';
    ch = commit_hash;
    wd = '--word-diff';
    
    sp = subprocess.Popen(('git %s %s show %s %s' % (gd,wt,ch,wd)),
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    #print('git %s %s show %s %s' % (gd,wt,ch,wd));
    (git_show_str, _) = sp.communicate();
    
    return git_show_str;


#
def get_committed_files_dict(committed_files_str):
    
    committed_files_strs = committed_files_str.split('\ndiff --git ');#committed_files_str.split('diff --git a/');
    del committed_files_strs[0]; # This item will always be the empty str, ''.
    
    committed_files_dict = dict();
    for cf_str in committed_files_strs:
    
        cf_str_lines = cf_str.splitlines();
        dict_key = 'diff --git ' + cf_str_lines[0];
        #dict_key = dict_key.decode();
        #print dict_key
        del cf_str_lines[0];

        committed_files_dict[dict_key] = cf_str_lines;

    return committed_files_dict;


# Store committed files records in DataFrame.
def make_commit_files_df(commit, commit_files):
    
    global repo_owner;
    global repo_name;
    
    row_labels = [r for r in range(0, len(commit_files))];
    
    COLUMN_LABELS = ['repo_owner', 'repo_name',
                     'path_in_repo', 'filename',
                     'commit_hash',
                     'author_name', 'author_email', 'author_epoch',
                     'committer_name', 'committer_email', 'committer_epoch',
                     'num_lines_changed', 'num_lines_inserted', 'num_lines_deleted', 'num_lines_modified'];
    
    commit_files_df = pandas.DataFrame(index=row_labels, columns=COLUMN_LABELS);
    
    for index, row in commit_files_df.iterrows():
        
        row['repo_owner'] = repo_owner;
        row['repo_name'] = repo_name;
        commit_file = commit_files[index]; # Get commit file dict at index.
        path_in_repo = commit_file['path_in_repo'];
        row['path_in_repo'] = path_in_repo if path_in_repo else '.'; # If path_in_repo is unspecified, file is in repo root.
        row['filename'] = commit_file['filename'];
        row['commit_hash'] = commit['commit_hash'];
        row['author_name'] = commit['author_name'];
        row['author_email'] = commit['author_email'];
        row['author_epoch'] = commit['author_epoch'];
        row['committer_name'] = commit['committer_name'];
        row['committer_email'] = commit['committer_email'];
        row['committer_epoch'] = commit['committer_epoch'];
        #row['subject'] = commit['subject'];
        row['num_lines_changed'] = commit_file['num_lines_changed'];
        row['num_lines_inserted'] = commit_file['num_lines_inserted'];
        row['num_lines_deleted'] = commit_file['num_lines_deleted'];
        row['num_lines_modified'] = commit_file['num_lines_modified'];

    return commit_files_df;


# Import project info to data store.
def push_project_info(project_record_df, title, data_store):
    
    if (os.path.exists(data_store)): # If data store already exists...
        ds_xls = pandas.ExcelFile(data_store); # Load Excel file.
        ds_df = ds_xls.parse(); # Convert Excel file to DataFrame.
        ds_df = pandas.concat([ds_df, project_record_df]); # Concatenate DataFrames.
        ds_df = ds_df.drop_duplicates().reset_index(drop=True); # Eliminate duplicate rows in DataFrame.
    else:
        ds_df = project_record_df;

    sh.write_df_to_file(ds_df, title, data_store);
    return;


# Calculate number of lines inserted, deleted, modified and the combined total for these.
def get_commit_changes(commit):
    
    global path_to_repo;
    
    commit['num_lines_changed'] = 0;
    commit['num_lines_inserted'] = 0;
    commit['num_lines_deleted'] = 0;
    commit['num_lines_modified'] = 0;
    
    partial_commit = False; # Signifies whether or not commit info in data store will only contain partial commit info.

    if (commit['filenames']):
        at_least_one = False;
    else:
        at_least_one = True;
    
    filenames = list();
    if (include_files): # This means the user directly specified commit files to process (i.e., some subset of all commit files)...
        for filename in include_files:
            if (filename in commit['filenames']):
                filenames.append(filename);
                partial_commit = True;
            else:
                print(sh.get_warning_str("No such file in repo \'" + str(filename) + "\'"));
    else: # All commit files...
        filenames = commit['filenames'];

    commit_files = list();

    commit_hash = commit['commit_hash'];
    committed_files_str = get_git_show_str(commit_hash);

    committed_files_dict = get_committed_files_dict(committed_files_str);
    
    for i in range(0, len(filenames)):
        
        filename = filenames[i];

        had_quotation_marks = False;
        if (filename.startswith("\"") and filename.endswith("\"")):
            filename = filename[1:-1];
            had_quotation_marks = True;

        repo_path = os.path.dirname(filename);
        repo_file = os.path.basename(filename);

        skip = False;
        for ep in exclude_paths:
            if (repo_path.startswith(ep)):
                skip = True;
        if (repo_file in exclude_files):
            skip = True;

        if (not skip):
        
            num_lines_changed = 0;
            num_lines_inserted = 0;
            num_lines_deleted = 0;
            num_lines_modified = 0;

            if (had_quotation_marks):
                #filename = filename.decode();
                #filename = re.sub(r'[^\w]', ' ', filename);
                #print repr(filename)
                k = 'diff --git \"a/%s\" \"b/%s\"' % (filename,filename);
                #print k
                #k = k.escape_decode#('\\\\', '\\');
                #print repr(k)
            else:
                k = 'diff --git a/%s b/%s' % (filename,filename);
            file_diff = committed_files_dict[k];
            (num_lines_inserted, num_lines_deleted, num_lines_modified) = get_changed_lines_info(file_diff);
            num_lines_changed = num_lines_inserted + num_lines_deleted + num_lines_modified;
    
            commit_file = dict();
            commit_file['path_in_repo'] = repo_path;
            commit_file['filename'] = repo_file;
            commit_file['num_lines_changed'] = num_lines_changed;
            commit_file['num_lines_inserted'] = num_lines_inserted;
            commit_file['num_lines_deleted'] = num_lines_deleted;
            commit_file['num_lines_modified'] = num_lines_modified;
            commit_files.append(commit_file);

            commit['num_lines_changed'] = commit['num_lines_changed'] + num_lines_changed;
            commit['num_lines_inserted'] = commit['num_lines_inserted'] + num_lines_inserted;
            commit['num_lines_deleted'] = commit['num_lines_deleted'] + num_lines_deleted;
            commit['num_lines_modified'] = commit['num_lines_modified'] + num_lines_modified;
            
            at_least_one = True;
        else:
            partial_commit = True;
    
    # Omit this functionaliy for now.
    #commit_files_df = make_commit_files_df(commit, commit_files);
    #files_data_store = args.data_store + '-files.xls';
    #push_project_info(commit_files_df, 'Files', files_data_store);

    if (partial_commit):
        commit['commit_hash'] = commit['commit_hash'] + '*';
    
    commit['filenames'] = filenames;
    commit['num_files_changed'] = len(filenames);
    del commit['filenames']; # (This field is no longer needed.)

    if (at_least_one):
        pass;
    else:
        commit = None;
    
    return commit;
    

# Parse project commit info.
def parse_commits(git_log_str):
    
    global path_to_repo;
    
    # Initial commit field names.
    COMMIT_FIELDS = ['commit_hash',
                     'author_name', 'author_email', 'author_epoch',
                     'committer_name', 'committer_email', 'committer_epoch',
                     'subject', 
                     'files_info'];
    
    log_values = git_log_str.strip('\n\x1e').split('\x1e');
    
    log_commits = [line.strip().split('\x1f') for line in log_values];
    
    commits = [dict(zip(COMMIT_FIELDS, line)) for line in log_commits];
    
    commit_count = len(commits);
    for i in range(0, commit_count):

        print("Processing commit " + str(i+1) + " of " + str(commit_count));
        
        commit = commits[i];

        commit['author_name'] = sh.make_ascii_str(commit['author_name']);
        commit['author_email'] = sh.make_ascii_str(commit['author_email']);
        commit['author_epoch'] = float(commit['author_epoch']);
        commit['committer_name'] = sh.make_ascii_str(commit['committer_name']);
        commit['committer_email'] = sh.make_ascii_str(commit['committer_email']);
        commit['committer_epoch'] = float(commit['committer_epoch']);
        commit['subject'] = sh.make_ascii_str(commit['subject']);
        
        if (args.anonymize):
            commit['author_name'] = sh.get_hash_str(commit['author_name']);
            commit['author_email'] = sh.get_hash_str(commit['author_email']);
            commit['committer_name'] = sh.get_hash_str(commit['committer_name']);
            commit['committer_email'] = sh.get_hash_str(commit['committer_email']);
            commit['subject'] = sh.get_hash_str(commit['subject']);
        
        commit['filenames'] = get_commit_filenames(commit['files_info']);
        del commit['files_info']; # (This field is no longer needed.)
        
        commit = get_commit_changes(commit);#, commit_hash);
        
        commits[i] = commit; # Update commit dict at position index 'i'.
    
    return commits;


# Get commits info as list of dicts, each dict representing a single commit.
# Inspired by a blog post by Steven Kryskalla: http://blog.lost-theory.org/post/how-to-parse-git-log-output/
def process_commits_info():
    
    global path_to_repo;
    global path_in_repo;
    
    # Git log commit fields.
    LOG_FORMAT = ['%H',
                  '%an', '%ae', '%at',
                  '%cn', '%ce', '%ct',
                  '%s'];
    
    log_format = '%x1e' + '%x1f'.join(LOG_FORMAT) + '%x1f';
    
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    wt = '--work-tree=\'' + path_to_repo + '\'';
    a = '--after=' + str(args.since);
    b = '--before=' + str(args.until);
    s = '--stat';
    stat_width = 1000; # Width of Git log output. (Using insanely-high number to ensure long filenames are captured correctly.)
    sw = '--stat-width=' + str(stat_width);
    f = '--format=' + str(log_format);
    p = '\'' + sh.add_path_to_uri(path_to_repo, path_in_repo) + '\'';
    
    sp = subprocess.Popen(('git %s %s log %s %s %s %s %s %s' % (gd,wt,a,b,s,sw,f,p)),
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    #print('git %s %s log %s %s %s %s %s \'%s\'' % (gd,wt,a,b,s,sw,f,p));
    (git_log_str, _) = sp.communicate();
    
    if (git_log_str):
        commits = parse_commits(git_log_str);
    else:
        return list();
    
    return commits;


# Fetch project commits info.
def get_commits():
    
    global path_to_repo;
    global path_in_repo;
    
    path_to_path_in_repo = sh.add_path_to_uri(path_to_repo, path_in_repo);
    
    if (sh.is_local_path(path_to_path_in_repo)):
        return process_commits_info();
    else:
        return list();


# Store project commit records in DataFrame.
def make_commit_record_df(commits):

    global repo_owner;
    global repo_name;
    global path_in_repo;
    #global path_to_repo;
    
    row_labels = [r for r in range(0, len(commits))];
    
    COLUMN_LABELS = ['repo_owner', 'repo_name',
                     'path_in_repo',
                     'commit_hash',
                     'author_name', 'author_email', 'author_epoch',
                     'committer_name', 'committer_email', 'committer_epoch',
                     'subject',
                     'num_files_changed',
                     'num_lines_changed', 'num_lines_inserted', 'num_lines_deleted', 'num_lines_modified'];
    
    commit_record_df = pandas.DataFrame(index=row_labels, columns=COLUMN_LABELS);
    
    for index, row in commit_record_df.iterrows():
        
        row['repo_owner'] = repo_owner;
        row['repo_name'] = repo_name;
        row['path_in_repo'] = path_in_repo;
        commit = commits[index];
        row['commit_hash'] = commit['commit_hash'];
        row['author_name'] = commit['author_name'];
        row['author_email'] = commit['author_email'];
        row['author_epoch'] = commit['author_epoch'];
        row['committer_name'] = commit['committer_name'];
        row['committer_email'] = commit['committer_email'];
        row['committer_epoch'] = commit['committer_epoch'];
        row['subject'] = commit['subject'];
        row['num_files_changed'] = commit['num_files_changed'];
        row['num_lines_changed'] = commit['num_lines_changed'];
        row['num_lines_inserted'] = commit['num_lines_inserted'];
        row['num_lines_deleted'] = commit['num_lines_deleted'];
        row['num_lines_modified'] = commit['num_lines_modified'];
    
    return commit_record_df;


# Process info for single project.
def process_project():
    
    potential_commits = get_commits();

    commits = list();
    for commit in potential_commits:
        if (commit is not None):
            commits.append(commit);

    if (commits):

        commits_data_store = args.data_store + '-commits.xls';

        commit_record_df = make_commit_record_df(commits);
        
        print("Importing " + str(len(commits)) + " commit records into data store...");
        push_project_info(commit_record_df, 'Commits', commits_data_store);
        
        print("Saved to \'" + commits_data_store + "\'.");
        return;
        
    else: # Commits list is empty...
        print(sh.get_warning_str("No relevant commits found"));
        return;


# Driver for scraper.
def main():
    
    global args;
    
    args = process_args();
    print('');
    check_args();
    print('');
    echo_args();
    print('');
    
    start = datetime.datetime.now();
    num_repos = len(args.sources);
    for i in range(0, num_repos):
        
        global path_to_repo;
        global repo_owner;
        global repo_name;

        rs_dict = args.sources[i];
        
        print("Processing repository " + str(i+1) + " of " + str(num_repos) + "...");
        
        repo_local_path = rs_dict['repo_uri'];
        print("LOCAL_PATH: " + repo_local_path);
        
        path_to_repo = os.path.abspath(repo_local_path);
        remote_origin_url = sh.get_remote_origin_url(path_to_repo);
        repo_owner, repo_name = extract_repo_owner_and_name(remote_origin_url);
        
        if (args.anonymize):
            repo_owner = sh.get_hash_str(repo_owner);
            repo_name = sh.get_hash_str(repo_name);
        
        paths_in_rs_dict = rs_dict['paths_in_repo'] if rs_dict['paths_in_repo'] else list();
        paths_in_repo = paths_in_rs_dict + args.paths_in_repo;
        paths_in_repo = list(set(paths_in_repo));
        global include_paths;
        global exclude_paths;
        include_paths = list();
        exclude_paths = list();
        for p in paths_in_repo:
            if (p.startswith('!')):
                exclude_paths.append(p[1:]);
            else:
                include_paths.append(p);
        if (not include_paths):
            include_paths.append('.');

        files_in_repo = args.files_in_repo + rs_dict['files_in_repo'];
        files_in_repo = list(set(files_in_repo));
        global include_files;
        global exclude_files;
        include_files = list();
        exclude_files = list();
        for f in files_in_repo:
            if (f.startswith('!')):
                exclude_files.append(f[1:]);
            else:
                include_files.append(f);

        not_paths_in_repo_str = ', '.join(["\'" + p + "\'" for p in exclude_paths]) if (exclude_paths) else "\'\'";
        files_in_repo_str = ', '.join(["\'" + f + "\'" for f in include_files]) if (include_files) else "\'*\'";
        not_files_in_repo_str = ', '.join(["\'" + f + "\'" for f in exclude_files]) if (exclude_files) else "\'\'";
        
        num_paths = len(include_paths);
        for j in range(0, num_paths): # For each path in repo...
            
            global path_in_repo;
            path_in_repo = include_paths[j];
            print("Processing path " + str(j+1) + " of " + str(num_paths) + "...");
            print("PATH: \'" + path_in_repo + "\'");
            print("IGNORE_PATHS: " + not_paths_in_repo_str + "");
            print("FILES: " + files_in_repo_str);
            print("IGNORE_FILES: " + not_files_in_repo_str);
            print('Accumulating project info...');
            proc_start_time = datetime.datetime.now();
            process_project();
            proc_end_time = datetime.datetime.now();
            proc_elapsed_time = proc_end_time - proc_start_time;
            print("Processing Time: " + str(proc_elapsed_time));
            print('Done.');
        
        print('');
    
    end = datetime.datetime.now();
    elapsed_time = end - start;
    print("Elapsed Time: " + str(elapsed_time));
    print("Execution Complete.");

    return;


main();


