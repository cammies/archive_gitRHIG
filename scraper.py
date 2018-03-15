#!/usr/bin/python


import argparse; # Script arguments.
import datetime; # Datetime handling.
import io; # File writing.
import itertools; # To count items in gernator.
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

github_hostname = ''; # Identifier for GitHub service.
repo_owner = ''; # Identifier for repository owner.
repo_name = ''; # Identifier for repository name.
path_in_repo = ''; # Path in repository commit log refers to.
labels_for_repo = None;


# Process script arguments.
def process_args():
    
    argparser = argparse.ArgumentParser();
    
    argparser.add_argument('-s','--sources', help="path to repository (relative to local working environment)", type=str);
    argparser.add_argument('-a','--anonymize', help="enforce anonymization on output commit records", action="store_true");
    argparser.add_argument('--data-store', help="destination data store (XLSX file) for commit records", type=str);
    argparser.add_argument('--paths', help="comma-separated string of repository subdirectories to process", type=str);
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
    args.paths = sh.get_paths_in_repo(args.paths);
    
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
   
    arg_paths_in_repo = ", ".join(["\'" + p + "\'" for p in args.paths]) if (args.paths) else "\'.\'";
    
    print("[global] Anonymize: " + str(args.anonymize));
    print("[global] Data store: \'" + args.data_store + '\'');
    print("[global] Paths: " + arg_paths_in_repo);
    print("[global] Since: " + args.since);
    print("[global] Until: " + args.until);


# Extract GitHub hostname, repo owner, and repo name from remote origin URL.
def get_repo_id(remote_origin_url):
    
    url = re.findall(r'^.+[://|@].+[:|/].+/.+', remote_origin_url);

    (github_hostname, repo_owner, repo_name) = re.findall(r'^.+[://|@](.+)[:|/](.+)/(.+)', url[0])[0];
    
    if (repo_name.endswith('.git')):
        repo_name = repo_name[:-4]; # Remove the '.git' from repo name.

    return github_hostname, repo_owner, repo_name;


# Parse information on files affected in a single commit.
def get_commit_filenames(files_str):
    
    #filenames_regex = r'\s+(.*)\s+\|\s+[a-zA-Z0-9]+';
    filenames_regex = r'\s+(.*[^\s]+)\s+\|\s+[a-zA-Z0-9]+'; # Better regex for git-log commit filenames.
    
    filenames = re.findall(filenames_regex, files_str);
    
    return filenames;


# Calculate number of lines inserted, deleted, modified.
def get_changed_lines_info(patch_str):
    
    #ADDITION_REGEX = re.compile(ur'\x1B\x5B\x33\x32\x6D\x7B\x2B[\s\S]*[\S]+[\s\S]*\x2B\x7D\x1B\x5B\x6D',
    #                            re.UNICODE);
    #ADDITION_START_END_REGEX = re.compile(ur'^\x1B\x5B\x33\x32\x6D\x7B\x2B[\s\S]*[\S]+[\s\S]*\x2B\x7D\x1B\x5B\x6D$',
    #                                      re.UNICODE);
    #REMOVAL_REGEX = re.compile(ur'\x1B\x5B\x33\x31\x6D\x5B\x2D[\s\S]*[\S]+[\s\S]*\x2D\x5D\x1B\x5B\x6D',
    #                           re.UNICODE);
    #REMOVAL_START_END_REGEX = re.compile(ur'^\x1B\x5B\x33\x31\x6D\x5B\x2D[\s\S]*[\S]+[\s\S]*\x2D\x5D\x1B\x5B\x6D$',
    #                                     re.UNICODE);
    ADDITION_REGEX = re.compile(ur'\x1B\[32m\{\+[\s\S]*[\S]+[\s\S]*\+\}\x1B\[m',
                                re.UNICODE);
    ADDITION_START_END_REGEX = re.compile(ur'^\x1B\[32m\{\+[\s\S]*[\S]+[\s\S]*\+\}\x1B\[m$',
                                          re.UNICODE);
    REMOVAL_REGEX = re.compile(ur'\x1B\[31m\[-[\s\S]*[\S]+[\s\S]*-\]\x1B\[m',
                               re.UNICODE);
    REMOVAL_START_END_REGEX = re.compile(ur'^\x1B\[31m\[-[\s\S]*[\S]+[\s\S]*-\]\x1B\[m$',
                                         re.UNICODE);
    
    num_lines_inserted = 0;
    num_lines_deleted = 0;
    num_lines_modified = 0;

    patch_str = patch_str.split('\n'); # Get string lines.

    for line in patch_str:
        
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


# Get git-log output str for a particular repository.
def get_gitlog_str():
    
    global path_to_repo;
    global path_in_repo;
    
    # git log commit fields.
    GITLOG_FIELDS = ['%H',
                     '%an', '%ae', '%at',
                     '%cn', '%ce', '%ct',
                     '%s'];
    
    gitlog_format = '\x1e\x1e\x1e' + '\x1f\x1f\x1f'.join(GITLOG_FIELDS) + '\x1f\x1f\x1f'; # Last '\x1f' accounts for files info field string.
    
    config = '-c color.diff.plain=\'normal\' -c color.diff.meta=\'normal bold\' -c color.diff.old=\'red\' -c color.diff.new=\'green\' -c color.diff.whitespace=\'normal\' -c color.ui=\'always\'';
    gd = '--git-dir=\'' + path_to_repo + '/.git/\'';
    wt = '--work-tree=\'' + path_to_repo + '\'';
    fh = '--full-history';
    a = '--since=\'' + since_dt_str + '\'';
    b = '--until=\'' + until_dt_str + '\'';
    s = '--stat';
    stat_width = 1000; # Length of git-log output. (Using insanely-high value to ensure "long" filenames are captured in their entirety.)
    sw = '--stat-width=' + str(stat_width);
    f = '--format=' + gitlog_format;
    patch = '-p';
    wd = '--word-diff=plain';
    p = '-- \'' + path_in_repo + '\'';
    
    cmd_str = 'git %s %s %s log %s %s %s %s %s %s %s %s %s' % (config,gd,wt,fh,a,b,s,sw,f,patch,wd,p);
    #print(cmd_str);

    sp = subprocess.Popen(cmd_str,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.STDOUT,
                          shell=True);
    
    (gitlog_str, _) = sp.communicate();
    
    return gitlog_str;


# Parse git-log output str and store info in DataFrame.
# Inspired by a blog post by Steven Kryskalla: http://blog.lost-theory.org/post/how-to-parse-git-log-output/
def get_commits_df():

    global github_hostname;
    global repo_owner;
    global repo_name;
    global path_in_repo;
    global labels_for_repo;

    sys.stdout.write("\r");
    sys.stdout.write("[git] Retrieving commit log: ...");
    sys.stdout.flush();
    t1 = datetime.datetime.now();
    
    gitlog_str = get_gitlog_str();
    
    t2 = datetime.datetime.now();
    t = t2 - t1;
    sys.stdout.write("\r");
    sys.stdout.write("[git] Retrieving commit log: done in {0}".format(t));
    print('');

    if (gitlog_str):

        commit_groups = (commit_group.strip('\x1e\x1e\x1e') for commit_group in gitlog_str.split('\n\x1e\x1e\x1e')); # Split commit records.

        (commit_groups, count_commit_groups) = itertools.tee(commit_groups, 2);
        num_commits = sum(1 for cg in count_commit_groups);
        
        ROW_LABELS = [r for r in range(0, num_commits)];
        
        COLUMN_LABELS = ['github_hostname', 'repo_owner', 'repo_name',
                         'path_in_repo',
                         'labels',
                         'commit_hash',
                         'author_name', 'author_email', 'author_epoch',
                         'committer_name', 'committer_email', 'committer_epoch',
                         'subject', 'len_subject',
                         'num_files_changed',
                         'num_lines_changed', 'num_lines_inserted', 'num_lines_deleted', 'num_lines_modified'];
        
        # Initial commit field names.
        COMMIT_FIELD_NAMES = ['commit_hash',
                              'author_name', 'author_email', 'author_epoch',
                              'committer_name', 'committer_email', 'committer_epoch',
                              'subject',
                              'patch_str'];
        
        commits_df = pandas.DataFrame(index=ROW_LABELS, columns=COLUMN_LABELS);
        
        t1 = datetime.datetime.now();
        j = 0; # Number records processed.
        k = 0.0; # Probability of records processed.
        for i in range(0, num_commits):

            commit_group = commit_groups.next();
            
            commit_fields = commit_group.split('\x1f\x1f\x1f');
            commit = dict(zip(COMMIT_FIELD_NAMES, commit_fields)); # Make commit dict.

            author_name = sh.decode_str(commit['author_name']);
            author_email = sh.decode_str(commit['author_email']);
            author_epoch = float(commit['author_epoch']);
            committer_name = sh.decode_str(commit['committer_name']);
            committer_email = sh.decode_str(commit['committer_email']);
            committer_epoch = float(commit['committer_epoch']);
            subject = sh.decode_str(commit['subject']);
            len_subject = len(subject);
            
            if (args.anonymize):
                author_name = sh.get_hash_str(author_name);
                author_email = sh.get_hash_str(author_email);
                committer_name = sh.get_hash_str(committer_name);
                committer_email = sh.get_hash_str(committer_email);
                subject = sh.get_hash_str(subject);
            
            patch_str = commit['patch_str'];
            files_str = patch_str.split('diff --git a/')[0];
            
            filenames = get_commit_filenames(files_str);

            (num_lines_inserted, num_lines_deleted, num_lines_modified) = get_changed_lines_info(patch_str);
            num_lines_changed = num_lines_inserted + num_lines_deleted + num_lines_modified;
        
            row = commits_df.iloc[i];

            row['github_hostname'] = github_hostname;
            row['repo_owner'] = repo_owner;
            row['repo_name'] = repo_name;
            row['path_in_repo'] = path_in_repo;
            row['labels'] = labels_for_repo;
            row['commit_hash'] = commit['commit_hash'];
            row['author_name'] = author_name;
            row['author_email'] = author_email;
            row['author_epoch'] = author_epoch;
            row['committer_name'] = committer_name;
            row['committer_email'] = committer_email;
            row['committer_epoch'] = committer_epoch;
            row['subject'] = subject;
            row['len_subject'] = len_subject;
            row['num_files_changed'] = len(filenames);
            row['num_lines_changed'] = num_lines_changed;
            row['num_lines_inserted'] = num_lines_inserted;
            row['num_lines_deleted'] = num_lines_deleted;
            row['num_lines_modified'] = num_lines_modified;
            
            j = j + 1;
            k = float(j) / float(num_commits);
            sys.stdout.write("\r");
            sys.stdout.write(("[git] Generating commit records: {0}% (" + str(j) + "/" + str(num_commits) + ")").format(int(100.0*k)));
            sys.stdout.flush();
        
        t2 = datetime.datetime.now();
        t = t2 - t1;
        sys.stdout.write("\r");
        sys.stdout.write(("[git] Generating commit records: {0}% (" + str(j) + "/" + str(num_commits) + "), done in {1}").format(int(100.0*k), t));

        print('');

        return commits_df;

    else:

        return pandas.DataFrame();


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

    commits_df = get_commits_df();
        
    if (not commits_df.empty):

        sys.stdout.write("\r");
        sys.stdout.write("[pandas] Importing commit records into data store: ...");
        sys.stdout.flush();
        
        t1 = datetime.datetime.now();
        
        push_commit_records(commits_df, 'commits', args.data_store);
        
        t2 = datetime.datetime.now();
        t = t2 - t1;
        sys.stdout.write("\r");
        sys.stdout.write("[pandas] Importing commit records into data store: done in {0}".format(t));
        print('');
        
        return True;    

    else: # Commits list is empty...
        print('\033[93m' + sh.get_warning_str("No relevant commits found") + '\033[m');
        return False;


# Driver for scraper.
def main():
    
    global args;
    global path_to_repo;
    global github_hostname;
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
    
    t1 = datetime.datetime.now();
    num_repos = len(args.sources);
    for i in range(0, num_repos):
        
        print("Processing repository " + str(i+1) + " of " + str(num_repos));
        
        source = args.sources[i];
        
        path_to_repo = source['uri'];
        print("[instance] Local path: \'" + path_to_repo + '\'');
        path_to_repo = os.path.abspath(path_to_repo);
        
        remote_origin_url = sh.get_remote_origin_url(path_to_repo);
        github_hostname, repo_owner, repo_name = get_repo_id(remote_origin_url);
        if (args.anonymize):
            github_hostname = sh.get_hash_str(github_hostname);
            repo_owner = sh.get_hash_str(repo_owner);
            repo_name = sh.get_hash_str(repo_name);

        paths = args.paths + source['paths_in_repo'];
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
            process_project();
        
        print('');
    
    t2 = datetime.datetime.now();
    t = t2 - t1;
    print("Elapsed time: " + str(t));

    return;


main();

