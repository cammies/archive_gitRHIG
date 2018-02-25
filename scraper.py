#!/usr/bin/python


import argparse; # Script arguments.
import datetime; # Datetime handling.
import io; # File writing.
import modules.shared as sh;
import os; # File system handling.
import pandas; # DataFrame handling.
import re; # Regular expressions.
import subprocess; # Invoke git applications.
import sys; # Script termination.
import time; # Ststem time.
import urlparse; # URL parsing.


# Global variables.

args = None; # For script arguments object.

ds_df = None; # Data store DataFrame.

path_to_repo = ''; # Local environment path to repository.

repo_owner = ''; # Identifier for repository owner.
repo_name = ''; # Identifier for repository name.
path_in_repo = ''; # Path in repository commit log refers to.
labels_for_repo = list();


# Process script arguments.
def process_args():
    
    argparser = argparse.ArgumentParser();
    
    argparser.add_argument('-s','--sources', help="path to repository (relative to local working environment)", type=str);
    argparser.add_argument('-a','--anonymize', help="enforce anonymization on output commit records", action="store_true");
    argparser.add_argument('--data-store', help="destination data store (XLSX file) for commit records", type=str);
    argparser.add_argument('--paths-in-repo', help="comma-separated string of repository subdirectories to process", type=str);
    argparser.add_argument('--labels', help="label commit records", type=str);
    argparser.add_argument('--since', help="scrape information about commits more recent than a specific date", type=str);
    argparser.add_argument('--until', help="scrape information about commits older than a specific date", type=str);
    
    return argparser.parse_args();


# Check script arguments.
def check_args():
    
    global ds_df;
    
    # Repo sources (URIs and corresponding paths).
    if (args.sources):
        args.sources = sh.get_repo_local_paths(args.sources);
    if (not args.sources):
        sys.exit("Must provide at least one valid repository URI.");
    
    # Output file.
    if (args.data_store):
       
        data_store = args.data_store;
        if (sh.is_writable_file(data_store)): # If destination data store is cleared for writing...
            
            if (os.path.exists(data_store)): # If destination data store already exists, check its structure...
                
                ds_df = sh.load_commits_data_store(data_store);
                if (ds_df is None):
                    sys.exit("Malformed data store \'" + data_store + "\'.");
            
            args.data_store = os.path.abspath(data_store);
        
        else:
            sys.exit();

    else: # Default output data store destination
        args.data_store = 'scraper-data_store-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S%f')[:-3] + '.xlsx';
    
    # Paths in repo.
    args.paths_in_repo = sh.get_paths_in_repo(args.paths_in_repo);
    
    # Label commit records.
    args.labels = sh.get_labels(args.labels);

    # 'Since' datetime string.
    since_dt_str = sh.get_since_dt_str(args.since);
    args.since = since_dt_str if since_dt_str else sh.get_utc_begin_str();
    
    # 'Until' datetime string.
    until_dt_str = sh.get_until_dt_str(args.until);
    args.until = until_dt_str if until_dt_str else sh.get_utc_now_str();
    

# Print script argument configurations.
def echo_args():
    
    arg_paths_in_repo = ", ".join(["\'" + p + "\'" for p in args.paths_in_repo]) if (args.paths_in_repo) else "\'.\'";
    
    print("[global] Anonymize: " + str(args.anonymize));
    print("[global] Data store: \'" + args.data_store + '\'');
    print("[global] Paths: " + arg_paths_in_repo);
    print("[global] Since: " + args.since);
    print("[global] Until: " + args.until);


# Extract repo owner and name from remote origin URL.
def extract_repo_owner_and_name(remote_origin_url):
    
    repo_owner = '';
    repo_name = '';
    
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(remote_origin_url);
    
    if (not scheme): # This is a git URL...
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
        filenames[i] = filenames[i].rstrip(); # (Strip leading, trailing spaces from filename str.)
    
    return filenames;


# Parse info from a single commit's log.
def get_gitshow_str(commit_hash):
    
    global path_to_repo;
    global path_in_repo;
    
    config = '-c color.diff.plain=\'normal\' -c color.diff.meta=\'normal bold\' -c color.diff.old=\'red\' -c color.diff.new=\'green\' -c color.diff.whitespace=\'normal\' -c color.ui=\'always\'';
    gd = '--git-dir=\'' + path_to_repo + '/.git/\''; # Wrap dir in quotation marks for safety (may contain spaces, etc.).
    wt = '--work-tree=\'' + path_to_repo + '\''; # Wrap dir in quotation marks for safety (may contain spaces, etc.).
    ch = commit_hash;
    wd = '--word-diff=plain';
    p = '-- \'' + path_in_repo + '\'';
    
    cmd_str = 'git %s %s %s show %s %s %s' % (config,gd,wt,ch,wd,p);
    #print(cmd_str);
    
    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    (git_show_str, _) = sp.communicate();
    
    return git_show_str;


#KEY_BEGIN = '\x1B\x5B\x31\x6D';

#KEY_END = '\x1B\x5B\x6D';

KEY_BEGIN = '\x1B[1m';
KEY_END = '\x1B[m';
ADDITION_REGEX = re.compile(ur'\x1B\[32m\{\+[\s\S]*[\S]+[\s\S]*\+\}\x1B\[m',
                            re.UNICODE);
ADDITION_START_END_REGEX = re.compile(ur'^\x1B\[32m\{\+[\s\S]*[\S]+[\s\S]*\+\}\x1B\[m$',
                                      re.UNICODE);
REMOVAL_REGEX = re.compile(ur'\x1B\[31m\[-[\s\S]*[\S]+[\s\S]*-\]\x1B\[m',
                           re.UNICODE);
REMOVAL_START_END_REGEX = re.compile(ur'^\x1B\[31m\[-[\s\S]*[\S]+[\s\S]*-\]\x1B\[m$',
                                     re.UNICODE);

#ADDITION_REGEX = re.compile(ur'\x1B\x5B\x33\x32\x6D\x7B\x2B[\s\S]*[\S]+[\s\S]*\x2B\x7D\x1B\x5B\x6D',
#                            re.UNICODE);

#ADDITION_START_END_REGEX = re.compile(ur'^\x1B\x5B\x33\x32\x6D\x7B\x2B[\s\S]*[\S]+[\s\S]*\x2B\x7D\x1B\x5B\x6D$',
#                                      re.UNICODE);

#REMOVAL_REGEX = re.compile(ur'\x1B\x5B\x33\x31\x6D\x5B\x2D[\s\S]*[\S]+[\s\S]*\x2D\x5D\x1B\x5B\x6D',
#                           re.UNICODE);

#REMOVAL_START_END_REGEX = re.compile(ur'^\x1B\x5B\x33\x31\x6D\x5B\x2D[\s\S]*[\S]+[\s\S]*\x2D\x5D\x1B\x5B\x6D$',
#                                     re.UNICODE);


#
def get_files_diff_dict(files_diff_str):
   
    files_diff_str = files_diff_str.split('\n' + KEY_BEGIN + 'diff --git ');
    del files_diff_str[0]; # First element not needed (EXPLAIN WHY).
    
    files_diff_dict = dict();
    for diff_str in files_diff_str:
   
        diff_str_lines = diff_str.splitlines();
        
        dict_key = KEY_BEGIN + 'diff --git ' + diff_str_lines[0]; # (First line used as other half of dict key).
        del diff_str_lines[0]; # Don't include (partial) dict key in file diff lines list. 

        files_diff_dict[dict_key] = diff_str_lines;

    return files_diff_dict;


# Get info on line insertions, deletions and modifications.
def get_changed_lines_info(file_diff_lines):
    
    num_lines_inserted = 0;
    num_lines_deleted = 0;
    num_lines_modified = 0;
    
    for line in file_diff_lines:
        
        line = line.strip();

        additions = re.findall(ADDITION_REGEX, line);
        removals = re.findall(REMOVAL_REGEX, line);
        
        if (additions and not removals): # Additions ONLY...
            if (ADDITION_START_END_REGEX.search(line)):
                if (len(additions) > 1):
                    num_lines_modified = num_lines_modified + 1;
                else:
                    num_lines_inserted = num_lines_inserted + 1;
            else:
                num_lines_modified = num_lines_modified + 1;
        elif (removals and not additions): # Removals ONLY...
            if (REMOVAL_START_END_REGEX.search(line)):
                if (len(removals) > 1):
                    num_lines_modified = num_lines_modified + 1;
                else:
                    num_lines_deleted = num_lines_deleted + 1;
            else:
                num_lines_modified = num_lines_modified + 1;
        elif (additions and removals): # Both additions AND removals...
            num_lines_modified = num_lines_modified + 1;
    
    return (num_lines_inserted, num_lines_deleted, num_lines_modified);


# Calculate number of lines inserted, deleted, modified and the combined total for these.
def get_commit_lines_changed_info(commit):
    
    commit['num_lines_changed'] = 0;
    commit['num_lines_inserted'] = 0;
    commit['num_lines_deleted'] = 0;
    commit['num_lines_modified'] = 0;
    
    commit_hash = commit['commit_hash']; 
    gitshow_str = get_gitshow_str(commit_hash);

    files_diff_dict = get_files_diff_dict(gitshow_str);
    
    filenames = commit['filenames'];
    for i in range(0, len(filenames)):
        
        filename = filenames[i];

        num_lines_changed = 0;
        num_lines_inserted = 0;
        num_lines_deleted = 0;
        num_lines_modified = 0;

        if (filename.startswith('\"') and filename.endswith('\"')):
            filename = filename[1:-1]; # Strip the quotation marks from filename string.
            files_diff_dict_key = ('diff --git ' + '\"' + 'a/%s' + '\" \"' + 'b/%s' + '\"') % (filename,filename);
        else:
            files_diff_dict_key = 'diff --git a/%s b/%s' % (filename,filename);

        files_diff_dict_key = KEY_BEGIN + files_diff_dict_key + KEY_END;
        file_diff_lines = files_diff_dict[files_diff_dict_key];
        
        (num_lines_inserted, num_lines_deleted, num_lines_modified) = get_changed_lines_info(file_diff_lines);
        num_lines_changed = num_lines_inserted + num_lines_deleted + num_lines_modified;

        commit['num_lines_changed'] = commit['num_lines_changed'] + num_lines_changed;
        commit['num_lines_inserted'] = commit['num_lines_inserted'] + num_lines_inserted;
        commit['num_lines_deleted'] = commit['num_lines_deleted'] + num_lines_deleted;
        commit['num_lines_modified'] = commit['num_lines_modified'] + num_lines_modified;
        
    return commit;
    

# Parse project commit info.
def process_commit_history(gitlog_str):
    
    # Initial commit field names.
    COMMIT_FIELDS = ['commit_hash',
                     'author_name', 'author_email', 'author_epoch',
                     'committer_name', 'committer_email', 'committer_epoch',
                     'subject', 
                     'files_info'];
    
    field_groups = gitlog_str.strip('\n\x1e').split('\x1e');
    
    field_records = [field_group.strip().split('\x1f') for field_group in field_groups];
    
    commits = [dict(zip(COMMIT_FIELDS, field_record)) for field_record in field_records];
    #print commits;
    
    t0_1 = datetime.datetime.now();
    commit_count = len(commits);
    for i in range(0, commit_count):
        
        #print("[git] Processing commit " + str(i+1) + " of " + str(commit_count));
        
        t1_1 = datetime.datetime.now();
        commit = commits[i];

        commit['author_name'] = sh.decode_str(commit['author_name']);
        commit['author_email'] = sh.decode_str(commit['author_email']);
        commit['author_epoch'] = float(commit['author_epoch']);
        commit['committer_name'] = sh.decode_str(commit['committer_name']);
        commit['committer_email'] = sh.decode_str(commit['committer_email']);
        commit['committer_epoch'] = float(commit['committer_epoch']);
        commit['subject'] = sh.decode_str(commit['subject']);
        commit['len_subject'] = len(commit['subject']);
        
        if (args.anonymize):
            commit['author_name'] = sh.get_hash_str(commit['author_name']);
            commit['author_email'] = sh.get_hash_str(commit['author_email']);
            commit['committer_name'] = sh.get_hash_str(commit['committer_name']);
            commit['committer_email'] = sh.get_hash_str(commit['committer_email']);
            commit['subject'] = sh.get_hash_str(commit['subject']);
        
        commit['filenames'] = get_commit_filenames(commit['files_info']);
        commit['num_files_changed'] = len(commit['filenames']);
        del commit['files_info']; # This field is no longer needed.
        
        commit = get_commit_lines_changed_info(commit);#, commit_hash);
        
        commits[i] = commit; # Update commit dict at position index 'i'.
        
        j = float(i+1)/float(commit_count);
        t1_2 = datetime.datetime.now();
        t = t1_2 - t1_1;
        t = (datetime.datetime.min + t).time();
        sys.stdout.write(("[git] Scraping commits: {0:.0f}% (" + str(i+1) + "/" + str(commit_count) + ") \r\x1b[K").format(100.0*j));
        sys.stdout.flush();
    
    t0_2 = datetime.datetime.now();
    t = t0_2 - t0_1;
    t = (datetime.datetime.min + t).time();
    sys.stdout.flush();
    sys.stdout.write(("[git] Scraping commits: {0:.0f}% (" + str(i+1) + "/" + str(commit_count) + ") in {1}").format(100.0*j, t.strftime('%H:%M:%S.%f')[:-3]));

    print('');
    
    return commits;


# Get commits info as list of dicts, each dict representing a single commit.
# Portions of code inspired by a blog post by Steven Kryskalla: http://blog.lost-theory.org/post/how-to-parse-git-log-output/
def get_commits():
    
    global path_to_repo;
    global path_in_repo;
    
    # git log commit fields.
    GITLOG_FIELDS = ['%H',
                     '%an', '%ae', '%at',
                     '%cn', '%ce', '%ct',
                     '%s'];
    
    gitlog_format = '\x1e' + '\x1f'.join(GITLOG_FIELDS) + '\x1f'; # Last '\x1f' accounts for files info field string.
    
    config = '';#'-c color.ui=\'false\'';
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    wt = '--work-tree=\'' + path_to_repo + '\'';
    a = '--since=\'' + since_dt_str + '\'';
    b = '--until=\'' + until_dt_str + '\'';
    s = '--stat';
    stat_width = 1000; # Length of git-log output. (Using insanely-high value to ensure "long" filenames are captured in their entirety.)
    sw = '--stat-width=' + str(stat_width);
    f = '--format=' + gitlog_format;
    p = '-- \'' + path_in_repo + '\'';
    
    cmd_str = 'git %s %s %s log %s %s %s %s %s %s' % (config,gd,wt,a,b,s,sw,f,p);
    print(cmd_str);

    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
    (gitlog_str, _) = sp.communicate();
    
    if (gitlog_str):
        commits = process_commit_history(gitlog_str);
        return commits;
    else:
        return list();


# Store project commit records in DataFrame.
def construct_commits_df(commits):

    global repo_owner;
    global repo_name;
    global path_in_repo;
    global labels_for_repo;
    
    num_records = len(commits);

    row_labels = [row_label for row_label in range(0, num_records)];
    
    COLUMN_LABELS = ['repo_owner', 'repo_name',
                     'path_in_repo',
                     'labels',
                     'commit_hash',
                     'author_name', 'author_email', 'author_epoch',
                     'committer_name', 'committer_email', 'committer_epoch',
                     'subject', 'len_subject',
                     'num_files_changed',
                     'num_lines_changed', 'num_lines_inserted', 'num_lines_deleted', 'num_lines_modified'];
    
    commits_df = pandas.DataFrame(index=row_labels, columns=COLUMN_LABELS);
    
    for i in range(0, num_records):
       
        row = commits_df.iloc[i];

        row['repo_owner'] = repo_owner;
        row['repo_name'] = repo_name;
        row['path_in_repo'] = path_in_repo;
        row['labels'] = labels_for_repo;
        commit = commits[i];
        row['commit_hash'] = commit['commit_hash'];
        row['author_name'] = commit['author_name'];
        row['author_email'] = commit['author_email'];
        row['author_epoch'] = commit['author_epoch'];
        row['committer_name'] = commit['committer_name'];
        row['committer_email'] = commit['committer_email'];
        row['committer_epoch'] = commit['committer_epoch'];
        row['subject'] = commit['subject'];
        row['len_subject'] = commit['len_subject'];
        row['num_files_changed'] = commit['num_files_changed'];
        row['num_lines_changed'] = commit['num_lines_changed'];
        row['num_lines_inserted'] = commit['num_lines_inserted'];
        row['num_lines_deleted'] = commit['num_lines_deleted'];
        row['num_lines_modified'] = commit['num_lines_modified'];
    
    return commits_df;


# Export DataFrame to file.
def push_commit_records(commits_df, title, destination):
    
    global ds_df;

    if (ds_df is not None): # If destination already exists...
        ds_df = pandas.concat([ds_df, commits_df]); # Concatenate existing commits DataFrame (from data store) with commits DataFrame.
        ds_df = ds_df.drop_duplicates().reset_index(drop=True); # Eliminate any duplicate DataFrame rows.
    else:
        ds_df = commits_df;

    sh.write_df_to_file(ds_df, title, destination);
    
    return;


# Process info for single project.
def process_project():
    
    commits = get_commits();

    if (commits):

        commits_df = construct_commits_df(commits);
        
        push_commit_records(commits_df, 'commits', args.data_store);
        print("[pandas] Importing commit records into data store");
        
        return True;    

    else: # Commits list is empty...
        print('\033[93m' + sh.get_warning_str("No relevant commits found") + '\033[m');
        return False;


# Driver for scraper.
def main():
    
    global args;
    global path_to_repo;
    global repo_owner;
    global repo_name;
    global path_in_repo;
    global labels_for_repo;
    global since_dt_str;
    global until_dt_str;

    args = process_args();
    print("Checking arguments");
    check_args();
    
    echo_args();
    print('');
    
    start = datetime.datetime.now();
    num_repos = len(args.sources);
    for i in range(0, num_repos):
        
        print("Processing repository " + str(i+1) + " of " + str(num_repos));
        
        source = args.sources[i];
        
        path_to_repo = source['uri'];
        print("[instance] Local path: \'" + path_to_repo + '\'');
        path_to_repo = os.path.abspath(path_to_repo);
        
        remote_origin_url = sh.get_remote_origin_url(path_to_repo);
        repo_owner, repo_name = extract_repo_owner_and_name(remote_origin_url);
        if (args.anonymize):
            repo_owner = sh.get_hash_str(repo_owner);
            repo_name = sh.get_hash_str(repo_name);

        paths = args.paths_in_repo + source['paths_in_repo'];
        paths = list(set(paths)); # Eliminate any duplicates.
        paths = paths if paths else ['.'];
        
        labels_for_repo = args.labels + source['labels_for_repo'];
        labels_for_repo = tuple(list(set(labels_for_repo))); # Eliminate any duplicates.

        since = '';
        if (len(source['since']) > 1):
            print(sh.get_warning_str("Too many \'since\' dates"));
        elif (len(source['since']) == 1):
            since = source['since'][0]; # Only elem in list.
        since = sh.get_since_dt_str(since) if since else since; # To potentially prevent unnecessary function call.
        since_dt_str = since if since else args.since;
        
        until = '';
        if (len(source['until']) > 1):
            print(sh.get_warning_str("Too many \'until\' dates"));
        elif (len(source['until']) == 1):
            until = source['until'][0]; # Only elem in list.
        until = sh.get_until_dt_str(until) if until else until; # To potentially prevent unnecessary function call.
        until_dt_str = until if until else args.until;

        num_paths = len(paths);
        for j in range(0, num_paths): # For each path in repo...
            
            path_in_repo = paths[j];
            print("Processing repository path " + str(j+1) + " of " + str(num_paths));
            print("[instance] Path: \'" + path_in_repo + "\'");
            print("[instance] Since: " + since_dt_str);
            print("[instance] Until: " + until_dt_str);
            #proc_start_time = datetime.datetime.now();
            process_project();
            #proc_end_time = datetime.datetime.now();
            #proc_elapsed_time = proc_end_time - proc_start_time;
            #print("Processing Time: " + str(proc_elapsed_time));
            #print("Done.");
        
        print('');
    
    end = datetime.datetime.now();
    elapsed_time = end - start;
    print("Elapsed time: " + str(elapsed_time));

    return;


main();


