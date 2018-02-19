#!/usr/bin/python


import argparse; # Script arguments
import ast;
import bokeh.io; # Interactive graphs in Jupyter Notebook.
import bokeh.layouts; # Output HTML column layout.
import bokeh.models; # Graph y-range.
import bokeh.palettes; # Graph color pallettes.
import bokeh.plotting; # Graph plot handling.
import datetime;
import io; # File writing.
import math;
import modules.shared as sh;
import numpy; # CDF, histogram graphs.
import os; # File, directory handling.
import pandas; # DataFrame handling.
import sys; # Script termination.


# Global variables.

data_store = None; # **Mock database.**
since = ''; # View only metrics after a specific date.
until = ''; # View only metrics before a specific date.

args = ''; # For script arguments object.

commit_info_df = ''; # For data store DataFrame.
committed_files_df = ''; # For data store DataFrame.

figs_list = list(); # List of distribution figures.

xlsfiles = list(); # Keep track of output XLS filenames.


# Process script arguments.
def process_args():
    
    argparser = argparse.ArgumentParser();
    
    argparser.add_argument('--data-store', help="input data store", type=str);
    argparser.add_argument('--since', help="analyze information about commits records more recent than a specific date", type=str);
    argparser.add_argument('--until', help="analyze information about commits records older than a specific date", type=str);
    
    return argparser.parse_args();


def check_args():
    
    global ds_df;
    
    if (args.data_store):
       
        data_store = args.data_store;
            
        if (os.path.exists(data_store)): # If destination data store already exists, check its structure...
            
            ds_df = sh.load_commits_data_store(data_store);
            if (ds_df is None):
                sys.exit("Malformed data store \'" + data_store + "\'.");

            args.data_store = os.path.abspath(data_store);
        
        else:
            sys.exit("\'" + data_store + "\' does not refer to a data store.");
        
    else:
        sys.exit("Must specify an input data store!");
    
    # 'Since' datetime string.
    args.since = sh.get_since_dt_str(args.since);
    
    # 'Until' datetime string.
    args.until = sh.get_until_dt_str(args.until);


# Print script argument configurations.
def echo_args():
    
    print("DATA_STORE: \'" + args.data_store + "*\'");
    print("SINCE: " + str(args.since));
    print("UNTIL: " + str(args.until));


# Determine project (calculated) IDs from data store.
def get_project_ids(commits_df):

    project_ids_df = commits_df[['repo_owner', 'repo_name']];#, 'path_in_repo']];#, 'path_to_repo']];
    project_ids_df = project_ids_df.drop_duplicates().reset_index(drop=True);
    
    return project_ids_df;


# Get datetime delta metrics and project feature vector.
def get_project_summaries_df(commit_info_df, project_ids_df):
    
    COLUMN_LABELS = ['repo_owner',
                     'repo_name',
                     #'path_in_repo',
                     #'path_to_repo',
                     'total_num_commits',
                     #'total_num_files_changed',
                     'total_num_lines_changed',
                     'total_num_insertions',
                     'total_num_deletions',
                     'total_num_modifications'];
    
    summary_dfs = list();
    for i in range(0, project_ids_df.shape[0]): # For each project ID...
        
        project_id_row = project_ids_df.iloc[i]; # Get row for project ID.
        
        summary_df = pandas.DataFrame(index=[0], columns=COLUMN_LABELS);
        
        commit_hashes = list();
        #filenames = list();
        #num_files_changed = 0;
        num_lines_changed = 0;
        num_lines_inserted = 0;
        num_lines_deleted = 0;
        num_lines_modified = 0;
        for j in range(0, commit_info_df.shape[0]): # For each project commit record (row) in data store DataFrame...
            
            cf_df_row = commit_info_df.iloc[j];
            if (cf_df_row['repo_owner'] == project_id_row['repo_owner'] and
                cf_df_row['repo_name'] == project_id_row['repo_name']): # If project ID matches current project ID...
                
                commit_hashes.append(cf_df_row['commit_hash']);
                
                #filenames.append(cf_df_row['filename']);
                
                #filenames_tuple = ast.literal_eval(ds_df_row['filenames']);
                #filenames = filenames + filenames_tuple;
                
                num_lines_changed = num_lines_changed + cf_df_row['num_lines_changed'];
                num_lines_inserted = num_lines_inserted + cf_df_row['num_lines_inserted'];
                num_lines_deleted = num_lines_deleted + cf_df_row['num_lines_deleted'];
                num_lines_modified = num_lines_modified + cf_df_row['num_lines_modified'];
        
        summary_df.iloc[0]['repo_owner'] = project_id_row['repo_owner'];
        summary_df.iloc[0]['repo_name'] = project_id_row['repo_name'];
        summary_df.iloc[0]['total_num_commits'] = len(list(set(commit_hashes)));
        #summary_df.iloc[0]['total_num_files_changed'] = len(list(set(filenames)));
        summary_df.iloc[0]['total_num_lines_changed'] = num_lines_changed;
        summary_df.iloc[0]['total_num_insertions'] = num_lines_inserted;
        summary_df.iloc[0]['total_num_deletions'] = num_lines_deleted;
        summary_df.iloc[0]['total_num_modifications'] = num_lines_modified;
        
        summary_dfs.append(summary_df);
    
    summaries_df = pandas.concat(summary_dfs).reset_index();
    
    return summaries_df;


# Dict of commit attributes names in plain English.
attr_labels_dict = {'total_num_commits' : 'Total Number of Commits',
                    #'total_num_files_changed' : 'Total Number of Files Changed',
                    'total_num_lines_changed' : 'Total Number of Lines Changed',
                    'total_num_insertions' : 'Total Number of Lines Inserted',
                    'total_num_deletions' : 'Total Number of Lines Deleted',
                    'total_num_modifications' : 'Total Number of Lines Modified'}


# Plot histogram for some data set.
def process_histogram(data, xlabel, ylabel):
        
    data_size = len(data);
    
    hist, bin_edges = numpy.histogram(data, density=False);
    
    title = "Histogram (N=" + str(data_size) + ")";
    
    p = bokeh.plotting.figure(title=title,
                              x_axis_label=xlabel,
                              y_axis_label=ylabel);
    
    p.quad(top=hist, bottom=0, left=bin_edges[:-1], right=bin_edges[1:], line_color='black', fill_color='blue');
    
    global figs_list;
    figs_list.append(p);


# Plot Cumulative Distribution Function (CDF) for some data set.
# Inspired by user Amedeo's answer: https://stackoverflow.com/questions/24575869/read-file-and-plot-cdf-in-python.
def process_cdf(data, xlabel):

    data_size = len(data);

    data_set = sorted(set(data));
    bins = numpy.append(data_set, data_set[-1]+1);
    
    counts, bin_edges = numpy.histogram(data, bins=bins, density=False);

    counts = counts.astype(float) / float(data_size);

    cdf = numpy.cumsum(counts);
    
    title = "Cumulative Distribution Function (N=" + str(data_size) + ")";
    
    ylabel = "Probability";

    p = bokeh.plotting.figure(title=title,
                              x_axis_label=xlabel,
                              y_axis_label=ylabel,
                              y_range=bokeh.models.Range1d(0, 1, bounds='auto'));
    
    p.title.align='center';

    p.line(bin_edges[0:-1], cdf, line_color='red');
    p.circle(bin_edges[0:-1], cdf, line_color='red', fill_color='red');

    global figs_list;
    figs_list.append(p);


# Plot graphs for each project feature vector feature.
def process_distribution_figs(attr, project_summaries_df):

    attr_values = project_summaries_df[attr].tolist();

    attr_label = attr_labels_dict[attr];

    #process_histogram(attr_values, attr_label, 'Number of Projects');

    process_cdf(attr_values, attr_label);


# Get preliminary frequency distribution DataFrame for a group of project summaries for some attrbute.
def get_frequency_dist_df(attr, project_summaries_df, interval_df):
    
    interval_df = interval_df.sort_values(by=['>=']); # Sort.
    interval_df = interval_df.reset_index(drop=True); # Reset DataFrame index.
    
    num_projects = project_summaries_df.shape[0];
    
    num_intervals = interval_df.shape[0];
    
    row_indices = [i for i in range(0, num_intervals)];
    
    column_labels = [attr, '>=', '<', 'frequency', 'percentage_in_interval', 'cumulative_frequency', 'cumulative_percentage'];
    
    df = pandas.DataFrame(index=row_indices, columns=column_labels);
    df = df.fillna(0.0);
    
    for i in range(0, num_intervals): # For each interval...
        
        interval_row = interval_df.iloc[i];
        df.iloc[i]['>='] = interval_row['>='];
        df.iloc[i]['<'] = interval_row['<'];
        
        for j in range(0, num_projects): # For each project summary...
            
            project_summary_row = project_summaries_df.iloc[j];
            
            attr_value = project_summary_row[attr];
            
            if (float(attr_value) >= float(interval_row['>=']) and
                float(attr_value) < float(interval_row['<'])):

                df.iloc[i][attr] = attr_value;
                
                frequency = df.iloc[i]['frequency'];
                df.iloc[i]['frequency'] = frequency + 1;
                
                frequency = df.iloc[i]['frequency'];
                df.iloc[i]['percentage_in_interval'] = (float(frequency) / float(num_projects)) * 100.0;
                
                frequencies = [df.iloc[c]['frequency'] for c in range(0, i+1)]; # Get frequency totals (up to and including this one) as a list.
                df.iloc[i]['cumulative_frequency'] = sum(frequencies);
                
                cumulative_frequency = df.iloc[i]['cumulative_frequency'];
                df.iloc[i]['cumulative_percentage'] = (float(cumulative_frequency) / float(num_projects)) * 100.0;
    
    dfw = df.drop(['>=', '<'], axis=1);    
    
    pathname, file_ext = os.path.splitext(args.data_store);
    dir_name = os.path.dirname(pathname);
    filename = os.path.basename(pathname);
    xlsfile = dir_name + '/' + attr + '-' + filename + '.xlsx';
    sh.write_df_to_file(dfw, "frequency_distribution", xlsfile);
    global xlsfiles;
    xlsfiles.append(xlsfile);
    
    return df;


# Chop float at x decimals WITHOUT rounding.
# Inspired by user Imre Kerr's answer: https://stackoverflow.com/questions/17264733/remove-decimal-places-to-certain-digits-without-rounding
def chop_float(num, x):
    
    num_str = str(num);
    num_str = num_str[:num_str.find('.') + x + 1];
    chopped = float(num_str);
    
    return chopped;


# Calculate interval begin.
def get_interval_begin(num):
    
    interval_begin = None;
    if (float(num).is_integer()):
        interval_begin = num;
    else:
        interval_begin = chop_float(num, 5);
    
    return interval_begin;


# Calculate interval end.
def get_interval_end(num):
    
    interval_end = None;
    if (float(num).is_integer()):
        interval_end = num + 1;
    else:
        interval_end = chop_float(num, 5) + 0.01;
    
    return interval_end;


# Get frequency distribution DataFrame for a group of project summaries for some attrbute.
def get_project_attr_frequency_dist_df(attr, project_summaries_df):
    
    project_summaries_df = project_summaries_df.sort_values(by=[attr]); # Sort.
    project_summaries_df = project_summaries_df.reset_index(drop=True); # Reset DataFrame index.
    
    num_projects = project_summaries_df.shape[0];
    
    row_labels = [i for i in range(0, num_projects)];
    
    COLUMN_LABELS = ['repo_owner',
                     'repo_name',
                     #'path_in_repo',
                     #'path_to_repo',
                     attr,
                     '>=',
                     '<',
                     'frequency',
                     'percentage_in_interval',
                     'cumulative_frequency',
                     'cumulative_percentage'];
    
    df = pandas.DataFrame(index=row_labels, columns=COLUMN_LABELS);
    df.fillna(0.0);
    
    for i in range(0, num_projects): # For each project summary...
        
        project_summaries_row = project_summaries_df.iloc[i]; # Get project summary record (row).
        attr_value = project_summaries_row[attr]; # Get project attribute value.
        
        df.iloc[i]['>='] = get_interval_begin(attr_value);
        
        df.iloc[i]['<'] = get_interval_end(attr_value); # Calculate interval end.
    
    interval_df = df[['>=','<']];
    interval_df = interval_df.drop_duplicates().reset_index(drop=True); # Eliminate duplicates.
    
    frequency_dist_df = get_frequency_dist_df(attr, project_summaries_df, interval_df);
    
    num_frequency_dists = frequency_dist_df.shape[0];
    
    for i in range(0, num_projects): # For each project summary...
        
        project_summaries_row = project_summaries_df.iloc[i]; # Get project summary record (row).
        attr_value = project_summaries_row[attr]; # Get project attribute value.
        
        for j in range(0, num_frequency_dists):
            
            frequency_dist_row = frequency_dist_df.iloc[j];
            
            if (float(attr_value) >= float(frequency_dist_row['>=']) and
                float(attr_value) < float(frequency_dist_row['<'])):
                
                df.iloc[i]['repo_owner'] = project_summaries_row['repo_owner'];
                df.iloc[i]['repo_name'] = project_summaries_row['repo_name'];
                #df.iloc[i]['path_in_repo'] = project_summaries_row['path_in_repo'];
                #df.iloc[i]['path_to_repo'] = project_summaries_row['path_to_repo'];
                df.iloc[i][attr] = attr_value;
                df.iloc[i]['>='] = frequency_dist_row['>='];
                df.iloc[i]['<'] = frequency_dist_row['<'];
                df.iloc[i]['frequency'] = frequency_dist_row['frequency'];
                df.iloc[i]['percentage_in_interval'] = frequency_dist_row['percentage_in_interval'];
                df.iloc[i]['cumulative_frequency'] = frequency_dist_row['cumulative_frequency'];
                df.iloc[i]['cumulative_percentage'] = frequency_dist_row['cumulative_percentage'];
    
    df = df.sort_values(by=[attr]);
    
    return df;


# Driver for analyzer.
def main():
    
    global args;
    #global commit_info_df;
    #global committed_files_df;
    global ds_df;
    global xlsfiles;
    
    args = process_args();
    print('');
    check_args();
    print('');
    echo_args();
    print('');
    start = datetime.datetime.now();
    
    htmlfile = args.data_store + '.html';
    bokeh.plotting.output_file(htmlfile, title="Project Statistics");

    print("Identifying projects...");
    project_ids_df = get_project_ids(ds_df);
    print("Done.");
    
    print("Building project summaries...");
    project_summaries_df = get_project_summaries_df(ds_df, project_ids_df);
    print("Done.");
    
    num_projects = project_summaries_df.shape[0];    
    
    attributes = ['total_num_commits',
                  #'total_num_files_changed',
                  'total_num_lines_changed',
                  'total_num_insertions',
                  'total_num_deletions',
                  'total_num_modifications'];
    print("Generating project statistics...");
    for a in range(0, len(attributes)):
        attr = attributes[a];
        
        process_distribution_figs(attr, project_summaries_df);
        
        project_attr_frequency_dist_df = get_project_attr_frequency_dist_df(attr, project_summaries_df);
        
        pathname, file_ext = os.path.splitext(args.data_store);
        dir_name = os.path.dirname(pathname);
        filename = os.path.basename(pathname);
        xlsfile = dir_name + '/' + attr + '-all_repos-' + filename + '.xlsx';
        sh.write_df_to_file(project_attr_frequency_dist_df, attr, xlsfile);
        xlsfiles.append(xlsfile);
        #print("ATTRIBUTE: " + attr);
        #print("Frequency distribution saved to \'" + xlsfile + "\'.");
    print("Done.");
    print('');

    print("SPREADSHEET_PATHS:");
    for xlsfile in xlsfiles:
        print("-> " + xlsfile);
    print('');

    bokeh.io.save(bokeh.layouts.column(figs_list));
    print("HTML_PATH:");
    print("-> " + htmlfile);
    print('');

    end = datetime.datetime.now();
    elapsed_time = end - start;
    print("Elapsed Time: " + str(elapsed_time));
    print("Execution complete.");


main();


