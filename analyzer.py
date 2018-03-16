#!/usr/bin/python


import argparse; # Script arguments
import ast;
import bokeh.io; # Interactive graphs in Jupyter Notebook.
import bokeh.layouts; # Output HTML column layout.
import bokeh.models; # Graph y-range, Hover Tool.
import bokeh.palettes; # Graph color pallettes.
import bokeh.plotting; # Graph plot handling.
import datetime;
import io; # File writing.
#import math;
import modules.shared as sh;
import numpy; # CDF, histogram graphs.
import os; # File, directory handling.
import pandas; # DataFrame handling.
import sys; # Script termination.
import time; # Time processing.


# Global variables.

data_store = None; # **Mock database.**
since = ''; # View only metrics after a specific date.
until = ''; # View only metrics before a specific date.

args = ''; # For script arguments object.

commit_info_df = ''; # For data store DataFrame.
committed_files_df = ''; # For data store DataFrame.

iwidths_dict = None;
icounts_dict = None;

figs_list = list(); # List of distribution figures.

xlsfiles = list(); # Keep track of output XLS filenames.

font_size = "12pt"; # Font size for text in output graphs.

dtdeltas = list();

# Process script arguments.
def process_args():
    
    argparser = argparse.ArgumentParser();
    
    argparser.add_argument('--data-store', help="input data store", type=str);
    argparser.add_argument('--iwidths', help="interval width", type=str);
    argparser.add_argument('--icounts', help="interval count", type=str);
    argparser.add_argument('-d','--directory', help="runtime working directory", type=str);
    #argparser.add_argument('--dt-deltas', help="which datetime deltas to consider", type=str);
    argparser.add_argument('--labels', help="label commit records", type=str);
    argparser.add_argument('--since', help="analyze information about commits records more recent than a specific date", type=str);
    argparser.add_argument('--until', help="analyze information about commits records older than a specific date", type=str);
    
    return argparser.parse_args();


# Dict of each datetime delta and its corresponding named unit.
DTDELTA_LABELS = {'Y' : 'total_num_years_active',
                  'm' : 'total_num_months_active',
                  'd' : 'total_num_days_active',
                  'H' : 'total_num_hours_active',
                  'M' : 'total_num_minutes_active',
                  'S' : 'total_num_seconds_active'};

# List of recognized datetime delta units.
DTDELTA_CODES = ['Y', # 'year'
                 'm', # 'month'
                 'd', # 'day'
                 'H', # 'hour'
                 'M', # 'minute'
                 'S']; # 'second'


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
    
    global iwidths_dict;
    iwidths_dict = sh.get_intervals_dict(args.iwidths);
    
    global icounts_dict;
    icounts_dict = sh.get_intervals_dict(args.icounts);
    
    # Working directory.
    args.directory = sh.get_wd(args.directory);
    
    # Get valid DTDs.
    #dtd_codes = list();
    #if (args.dt_deltas):
    #    args.dt_deltas = sh.split_str(',', args.dt_deltas);
    #    for dtd_code in args.dt_deltas:
    #        if (dtd_code in DTD_CODES):
    #            dtd_codes.append(dtd_code);
    #        else:
    #            print(sh.get_warning_str("Unrecognized datetime delta code \'" + dtd_code + "\'"));
    #args.dt_deltas = list(set(dtd_codes));

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
    
    print("DATA_STORE: \'" + args.data_store + "\'");
    print("SINCE: " + str(args.since));
    print("UNTIL: " + str(args.until));


#
def prune_records(ds_df):

    since = float(sh.utc_str_to_epoch(args.since));
    until = float(sh.utc_str_to_epoch(args.until));

    init_num_records = ds_df.shape[0];

    drop_these = list(); # List of indices of corresponding DataFrame rows to drop.
    for i in range(0, init_num_records): # For each project commit record (row) in data store DataFrame...
        
        commit_record = ds_df.iloc[i];
        
        author_date = float(commit_record['author_epoch']);
        committer_date = float(commit_record['committer_epoch']);
        
        if (author_date < since or
            author_date > until or
            committer_date < since or
            committer_date > until):

            drop_these.append(i);
        
        elif (args.labels):
            
            commit_record_labels_tuple = ast.literal_eval(commit_record['labels']);
            include_commit_record = False;
            for label in args.labels: # For EACH user-supplied label...
                
                if (label in commit_record_labels_tuple): # If commit record includes label... 
                    include_commit_record = True; # Indicate to include this commit record in resulting DataFrame.
            
            if (not include_commit_record):
                drop_these.append(i);

    df = ds_df.drop(drop_these); # Drop DataFrame rows (given indices specifed).
    df = df.reset_index(drop=True); # Reset DataFrame row indices.
        
    return df;


# Determine project (calculated) IDs from data store.
def get_project_ids_df(ds_df):

    project_ids_df = ds_df[['github_hostname', 'repo_owner', 'repo_name', 'path_in_repo']];
    project_ids_df = project_ids_df.drop_duplicates(); # Eliminate duplicate DataFrame rows.
    project_ids_df = project_ids_df.reset_index(drop=True); # Reset DataFrame row indices.
    
    return project_ids_df;


# Plot repository timelines for some data set.
def process_timelines(df, p):
        
    data = dict(df);
    
    source = bokeh.plotting.ColumnDataSource(data=data);
    
    p.circle('committer_epoch', 'project_index', source=source, line_color='green', fill_color='green');
    p.line('committer_epoch', 'project_index', source=source, line_color='green');
    
    return p;


# Get plot containing development timeline for each repository.
def get_commit_patterns(project_ids_df, ds_df):
    
    global figs_list;
    
    num_projects = project_ids_df.shape[0];
    
    committer_dates = list();
    for i, row in ds_df.iterrows(): # Format committer dates.

        dt = datetime.datetime.fromtimestamp(float(row["committer_epoch"]));
        ds_df.loc[i, 'committer_epoch'] = dt;
        
        committer_dates.append(dt.strftime("%Y-%m-%d %H:%M:%S " + time.tzname[1])); # (Account for Daylight Saving Time.)

    ds_df['committer_date'] = committer_dates; # Add new column for committer dates as strings.
    
    hover = bokeh.models.HoverTool(tooltips=[('github_hostname', '@github_hostname'),
                                             ('repo_owner', '@repo_owner'),
                                             ('repo_name', '@repo_name'),
                                             ('path_in_repo', '@path_in_repo'),
                                             ('date', '@committer_date'),
                                             ('num_lines_changed', '@num_lines_changed'),
                                             ('num_lines_inserted', '@num_lines_inserted'),
                                             ('num_lines_deleted', '@num_lines_deleted'),
                                             ('num_lines_modified', '@num_lines_modified')]);
    
    title = "Commit Patterns (N=" + str(num_projects) + ")";
    
    p = bokeh.plotting.figure(#plot_width=400,
                              #plot_height=400,
                              tools=[hover, 'wheel_zoom', 'box_zoom', 'pan', 'save, ''reset'],
                              title=title,
                              x_axis_label="Time",
                              x_axis_type='datetime',
                              y_axis_label="Repository"
                              );
    
    p.title.align='center';
    p.title.text_font_size=font_size;
    p.xaxis.major_label_text_font_size=font_size;
    p.xaxis.axis_label_text_font_size=font_size;
    p.yaxis.major_label_text_font_size='0pt';
    p.yaxis.axis_label_text_font_size=font_size;

    for j in range(0, num_projects): # For each project...

        df = ds_df[(ds_df['repo_owner'] == project_ids_df.iloc[j]['repo_owner']) &
                   (ds_df['repo_name'] == project_ids_df.iloc[j]['repo_name'])];
        
        pindex = [j+1 for k in range(0, df.shape[0])];
        df = df.assign(project_index= pindex);
        p = process_timelines(df, p);

    figs_list.append(p);


# Get datetime delta strftime-like string corresponding to datetime delta code.
def get_dtdelta_str(dt, dtdelta_code):
   
    if (dtdelta_code == 'Y'):
        return dt.strftime('%Y');
    elif (dtdelta_code == 'm'):
        return dt.strftime('%Y-%m');
    elif (dtdelta_code == 'd'):
        return dt.strftime('%Y-%m-%d');
    elif (dtdelta_code == 'H'):
        return dt.strftime('%Y-%m-%d %H:00:00');
    elif (dtdelta_code == 'M'):
        return dt.strftime('%Y-%m-%d %H:%M:00');
    elif (dtdelta_code == 'S'):
        return dt.strftime('%Y-%m-%d %H:%M:%S');


# Convert UNIX epoch to local UTC timestamp. 
def epoch_to_local_utc(epoch):
    
    return datetime.datetime.fromtimestamp(float(epoch));


# Get number of datetime deltas given some list of epochs.
def get_num_dtdeltas(epochs, dtdelta_code):

    dtdeltas = list();
    for epoch in epochs:

        dt = epoch_to_local_utc(epoch);
        dtdelta_str = get_dtdelta_str(dt, dtdelta_code);
        dtdeltas.append(dtdelta_str);

    dtdeltas = list(set(dtdeltas));

    num_dtdeltas = len(dtdeltas);

    return num_dtdeltas;


# Get datetime delta metrics and project feature vector.
def get_project_summaries_df(features, project_ids_df, ds_df):
    
    project_id_labels = ['github_hostname',
                         'repo_owner',
                         'repo_name',
                         'path_in_repo'];

    COLUMN_LABELS = project_id_labels + features;
    
    num_projects = project_ids_df.shape[0];
    
    ROW_LABELS = [r for r in range(0, num_projects)];
    
    project_summaries_df = pandas.DataFrame(index=ROW_LABELS, columns=COLUMN_LABELS);
    
    num_commits_record = ds_df.shape[0];
    
    for i in range(0, num_projects): # For each project (from ID)...
        
        project_id = project_ids_df.iloc[i]; # Get project ID.
        
        commit_hashes = list();
        epochs = list();
        num_lines_changed = 0;
        num_lines_inserted = 0;
        num_lines_deleted = 0;
        num_lines_modified = 0;
        for j in range(0, num_commits_record): # For each commit record (row) in data store DataFrame...
            
            commit_record = ds_df.iloc[j]; # Get commit record.

            if (commit_record['github_hostname'] == project_id['github_hostname'] and
                commit_record['repo_owner'] == project_id['repo_owner'] and
                commit_record['repo_name'] == project_id['repo_name'] and
                commit_record['path_in_repo'] == project_id['path_in_repo']): # If commit record project ID matches project ID...
            
                commit_hashes.append(commit_record['commit_hash']);
                 
                epochs = epochs + [commit_record['author_epoch'], commit_record['committer_epoch']];
                    
                num_lines_changed = num_lines_changed + commit_record['num_lines_changed'];
                num_lines_inserted = num_lines_inserted + commit_record['num_lines_inserted'];
                num_lines_deleted = num_lines_deleted + commit_record['num_lines_deleted'];
                num_lines_modified = num_lines_modified + commit_record['num_lines_modified'];

            project_summaries_df.iloc[i]['github_hostname'] = project_id['github_hostname'];
            project_summaries_df.iloc[i]['repo_owner'] = project_id['repo_owner'];
            project_summaries_df.iloc[i]['repo_name'] = project_id['repo_name'];
            project_summaries_df.iloc[i]['path_in_repo'] = project_id['path_in_repo'];
            project_summaries_df.iloc[i]['total_num_commits'] = len(list(set(commit_hashes)));
            project_summaries_df.iloc[i]['total_num_lines_changed'] = num_lines_changed;
            project_summaries_df.iloc[i]['total_num_lines_inserted'] = num_lines_inserted;
            project_summaries_df.iloc[i]['total_num_lines_deleted'] = num_lines_deleted;
            project_summaries_df.iloc[i]['total_num_lines_modified'] = num_lines_modified;
            
            global dtdeltas;
            for dtdelta_code in dtdeltas:

                num_dtdeltas = get_num_dtdeltas(epochs, dtdelta_code);
                dtdelta_label = DTDELTA_LABELS[dtdelta_code];
                project_summaries_df.iloc[i][dtdelta_label] = num_dtdeltas; 
        
    return project_summaries_df;


# Dict of commit attributes names in plain English.
feature_titles_dict = {'total_num_commits' : 'Total Number of Commits',
                       #'total_num_files_changed' : 'Total Number of Files Changed',
                       'total_num_lines_changed' : 'Total Number of Lines Changed',
                       'total_num_lines_inserted' : 'Total Number of Lines Inserted',
                       'total_num_lines_deleted' : 'Total Number of Lines Deleted',
                       'total_num_lines_modified' : 'Total Number of Lines Modified',
                       'total_num_years_active' : 'Total Number of Years Active',
                       'total_num_months_active' : 'Total Number of Months Active',
                       'total_num_days_active' : 'Total Number of Days Active',
                       'total_num_hours_active' : 'Total Number of Hours Active',
                       'total_num_minutes_active' : 'Total Number of Minutes Active',
                       'total_num_seconds_active' : 'Total Number of Seconds Active'}


# Plot histogram for some data set.
def process_histogram(data, xlabel, ylabel):
    
    global figs_list;
    global font_size;
    
    data_size = len(data);
    
    num_bins = max(data);

    hist, bin_edges = numpy.histogram(data, density=False, bins=num_bins);
    
    title = "Histogram (N=" + str(data_size) + ")";
    
    p = bokeh.plotting.figure(title=title,
                              x_axis_label=xlabel,
                              y_axis_label=ylabel);
    
    p.quad(top=hist, bottom=0, left=bin_edges[:-1], right=bin_edges[1:], line_color='black', fill_color='blue');
    
    p.title.align='center';
    p.title.text_font_size=font_size;
    p.xaxis.major_label_text_font_size=font_size;
    p.xaxis.axis_label_text_font_size=font_size;
    p.yaxis.major_label_text_font_size=font_size;
    p.yaxis.axis_label_text_font_size=font_size;

    figs_list.append(p);


#
def process_new_histogram(feature_freq_dist_df, p):
        
    data = dict(feature_freq_dist_df);
    
    source = bokeh.plotting.ColumnDataSource(data=data);
    
    p.quad(top='frequency', bottom='bottom', left='>=', right='<', source=source, line_color='black', fill_color='blue');

    return p;


# Get plot containing development timeline for each repository.
def get_histogram(feature, feature_freq_dist_df):
    
    global figs_list;
    
    num_projects = feature_freq_dist_df.shape[0];

    feature_freq_dist_df['bottom'] = [0 for b in range(0, num_projects)];
    
    hover = bokeh.models.HoverTool(tooltips=[('github_hostname', '@github_hostname'),
                                             ('repo_owner', '@repo_owner'),
                                             ('repo_name', '@repo_name'),
                                             ('path_in_repo', '@path_in_repo'),
                                             (feature, '@'+feature)]);
    
    title = "Histogram (N=" + str(num_projects) + ")";
    
    feature_title = feature_titles_dict[feature];

    p = bokeh.plotting.figure(#plot_width=400,
                              #plot_height=400,
                              tools=[hover, 'wheel_zoom', 'box_zoom', 'pan', 'save, ''reset'],
                              title=title,
                              x_axis_label=feature_title,
                              y_axis_label='Number of Repositories',
                              );
    
    p.title.align='center';
    p.title.text_font_size=font_size;
    p.xaxis.major_label_text_font_size=font_size;
    p.xaxis.axis_label_text_font_size=font_size;
    p.yaxis.major_label_text_font_size=font_size;
    p.yaxis.axis_label_text_font_size=font_size;

    p = process_new_histogram(feature_freq_dist_df, p);

    figs_list.append(p);


# Plot Cumulative Distribution Function (CDF) for some data set.
# Inspired by user Amedeo's answer: https://stackoverflow.com/questions/24575869/read-file-and-plot-cdf-in-python.
def process_cdf(data, xlabel):

    global figs_list;
    global font_size;
    
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
    p.title.text_font_size=font_size;
    p.xaxis.major_label_text_font_size=font_size;
    p.xaxis.axis_label_text_font_size=font_size;
    p.yaxis.major_label_text_font_size=font_size;
    p.yaxis.axis_label_text_font_size=font_size;

    p.line(bin_edges[0:-1], cdf, line_color='red');
    p.circle(bin_edges[0:-1], cdf, line_color='red', fill_color='red');

    figs_list.append(p);


# Plot graphs for each project feature vector feature.
def process_distribution_figs(feature, project_summaries_df):

    feature_values = project_summaries_df[feature].tolist();

    feature_title = feature_titles_dict[feature];

    process_histogram(feature_values, feature_title, 'Number of Projects');

    process_cdf(feature_values, feature_title);


# Chop float at x decimals WITHOUT rounding.
# Inspired by user Imre Kerr's answer: https://stackoverflow.com/questions/17264733/remove-decimal-places-to-certain-digits-without-rounding
def chop_float(num, x):
    
    num_str = str(num);
    num_str = num_str[:num_str.find('.') + x + 1];
    chopped = float(num_str);
    
    return chopped;


# Calculate interval begin.
def calc_interval_begin(num):
    
    interval_begin = None;
    if (float(num).is_integer()):
        interval_begin = num;
    else:
        interval_begin = chop_float(num, 5);
    
    return interval_begin;


# Calculate interval end.
def calc_interval_end(num):
    
    interval_end = None;
    if (float(num).is_integer()):
        interval_end = num + 1;
    else:
        interval_end = chop_float(num, 5) + 0.01;
    
    return interval_end;


#
def get_feature_intervals_df(feature, project_summaries_df):
    
    COLUMN_LABELS = ['>=', '<'];

    df = pandas.DataFrame();

    global iwidths_dict;
    global icounts_dict;
    
    if (feature in iwidths_dict or
        feature in icounts_dict):

        print("Attribute \'" + feature + "\' found");

        values = project_summaries_df[feature].tolist();

        max_val = max(values);

        if (feature in iwidths_dict):

            iwidth = int(iwidths_dict[feature]);

            num_intervals = int(max_val / iwidth) + 1;

        else: # feature is in icounts_dict...

            icount = int(icounts_dict[feature]);

            num_intervals = icount + 1;

            iwidth = int(max_val / icount) + 1;

        ROW_LABELS = [i for i in range(0, num_intervals+1)]; # '+1' because 0-1 will be its own interval.
            
        df = pandas.DataFrame(index=ROW_LABELS, columns=COLUMN_LABELS);
        df.fillna(0.0);
            
        df.iloc[0]['>='] = 0; # First interval will be from 0...
        df.iloc[0]['<'] = 1; # ...to 1.
        for i in range(0, num_intervals):

            from_value = i * iwidth;
            to_value = from_value + iwidth;
            df.iloc[i+1]['>='] = calc_interval_begin(from_value+1); # '+1' to skip 0 in first loop.
            df.iloc[i+1]['<'] = calc_interval_end(to_value);

    else: # If user-defined interval info was left unspecified, use 1-unit width intervals.
        
        num_intervals = project_summaries_df.shape[0];
        
        ROW_LABELS = [r for r in range(0, num_intervals)];
    
        df = pandas.DataFrame(index=ROW_LABELS, columns=COLUMN_LABELS);
        df.fillna(0.0);
        
        for i in range(0, num_intervals): # For each project summary...
            
            from_value = project_summaries_df.iloc[i][feature]; # Get feature value for project i.
            to_value = from_value; # (Since in this case, interval width is only a single unit.)
            
            df.iloc[i]['>='] = calc_interval_begin(from_value);
            df.iloc[i]['<'] = calc_interval_end(to_value);
    
    intervals_df = df[['>=','<']];
    intervals_df = intervals_df.drop_duplicates(); # Eliminate duplicate DataFrame rows.
    intervals_df = intervals_df.reset_index(drop=True); # Reset DataFrame row indices.

    return intervals_df;


# Get preliminary frequency distribution DataFrame for a group of project summaries for some feature.
def get_freq_dist_df(feature, project_summaries_df, feature_intervals_df):
    
    feature_intervals_df = feature_intervals_df.sort_values(by=['>=']); # Sort DataFrame rows by interval begin-value.
    feature_intervals_df = feature_intervals_df.reset_index(drop=True); # Reset DataFrame row indices.
    
    num_projects = project_summaries_df.shape[0];
    
    num_intervals = feature_intervals_df.shape[0];
    
    ROW_LABELS = [r for r in range(0, num_intervals)];
    
    COLUMN_LABELS = [feature, '>=', '<', 'frequency', 'cumulative_frequency', 'percentage', 'cumulative_percentage'];
    
    df = pandas.DataFrame(index=ROW_LABELS, columns=COLUMN_LABELS);
    df = df.fillna(0.0);
    
    for i in range(0, num_intervals): # For each interval...
        
        feature_interval = feature_intervals_df.iloc[i];
        df.iloc[i]['>='] = feature_interval['>='];
        df.iloc[i]['<'] = feature_interval['<'];
        
        for j in range(0, num_projects): # For each project summary...
            
            project_summary = project_summaries_df.iloc[j];
            
            feature_value = project_summary[feature];
            
            if (float(feature_value) >= float(feature_interval['>=']) and
                float(feature_value) < float(feature_interval['<'])):

                df.iloc[i][feature] = feature_value;
                
                frequency = df.iloc[i]['frequency'];
                df.iloc[i]['frequency'] = frequency + 1;
                
                frequencies = [df.iloc[c]['frequency'] for c in range(0, i+1)]; # Get frequency totals (up to and including this one) as a list.
                df.iloc[i]['cumulative_frequency'] = sum(frequencies);
                
                frequency = df.iloc[i]['frequency'];
                df.iloc[i]['percentage'] = (float(frequency) / float(num_projects)) * 100.0;
                
                cumulative_frequency = df.iloc[i]['cumulative_frequency'];
                df.iloc[i]['cumulative_percentage'] = (float(cumulative_frequency) / float(num_projects)) * 100.0;
    
    return df;


# Get frequency distribution DataFrame for a group of project summaries for some feature.
def get_feature_freq_dist_df(feature, project_summaries_df):
    
    project_summaries_df = project_summaries_df.sort_values(by=[feature]); # Sort by values in feature observations.
    project_summaries_df = project_summaries_df.reset_index(drop=True); # Reset DataFrame indice.
    
    num_projects = project_summaries_df.shape[0];
    
    ROW_LABELS = [r for r in range(0, num_projects)];
    
    COLUMN_LABELS = ['github_hostname',
                     'repo_owner',
                     'repo_name',
                     'path_in_repo',
                     feature,
                     '>=',
                     '<',
                     'frequency',
                     'cumulative_frequency',
                     'percentage',
                     'cumulative_percentage'];
    
    df = pandas.DataFrame(index=ROW_LABELS, columns=COLUMN_LABELS);
    df.fillna(0.0);
    
    feature_intervals_df = get_feature_intervals_df(feature, project_summaries_df);
    
    freq_dist_df = get_freq_dist_df(feature, project_summaries_df, feature_intervals_df);
    
    num_freq_dists = freq_dist_df.shape[0];
    
    for i in range(0, num_projects): # For each project summary...
        
        project_summary = project_summaries_df.iloc[i]; # Get project summary record (row).
        feature_value = project_summary[feature]; # Get project attribute value.
        
        for j in range(0, num_freq_dists):
            
            freq_dist = freq_dist_df.iloc[j];
            
            if (float(feature_value) >= float(freq_dist['>=']) and
                float(feature_value) < float(freq_dist['<'])):
                
                df.iloc[i]['github_hostname'] = project_summary['github_hostname'];
                df.iloc[i]['repo_owner'] = project_summary['repo_owner'];
                df.iloc[i]['repo_name'] = project_summary['repo_name'];
                df.iloc[i]['path_in_repo'] = project_summary['path_in_repo'];
                df.iloc[i][feature] = feature_value;
                df.iloc[i]['>='] = freq_dist['>='];
                df.iloc[i]['<'] = freq_dist['<'];
                df.iloc[i]['frequency'] = freq_dist['frequency'];
                df.iloc[i]['cumulative_frequency'] = freq_dist['cumulative_frequency'];
                df.iloc[i]['percentage'] = freq_dist['percentage'];
                df.iloc[i]['cumulative_percentage'] = freq_dist['cumulative_percentage'];
    
    df = df.sort_values(by=[feature]);
    
    return df;


# Plot CDF for some feature.
def process_new_cdf(feature, feature_freq_dist_df, p):
        
    data = dict(feature_freq_dist_df);
    
    source = bokeh.plotting.ColumnDataSource(data=data);
    
    p.circle(feature, 'cumulative_probability', source=source, line_color='red', fill_color='red');
    p.line(feature, 'cumulative_probability', source=source, line_color='red');
    
    return p;


# Get plot containing development timeline for each repository.
def get_cdf(feature, feature_freq_dist_df):
    
    global figs_list;
    
    num_projects = feature_freq_dist_df.shape[0];
    
    cumulative_probabilities = list();
    for i, row in feature_freq_dist_df.iterrows(): # Format committer dates.

        cumulative_percentage = float(row['cumulative_percentage']);
        
        cumulative_probability = cumulative_percentage / 100.0;

        cumulative_probabilities.append(cumulative_probability);

    feature_freq_dist_df['cumulative_probability'] = cumulative_probabilities; # Add new column for CDF data as strings.
    
    hover = bokeh.models.HoverTool(tooltips=[('github_hostname', '@github_hostname'),
                                             ('repo_owner', '@repo_owner'),
                                             ('repo_name', '@repo_name'),
                                             ('path_in_repo', '@path_in_repo'),
                                             (feature, '@'+feature)]);
    
    title = "Cumulative Distribution Function (N=" + str(num_projects) + ")";
    
    feature_title = feature_titles_dict[feature];

    p = bokeh.plotting.figure(#plot_width=400,
                              #plot_height=400,
                              tools=[hover, 'wheel_zoom', 'box_zoom', 'pan', 'save, ''reset'],
                              title=title,
                              x_axis_label=feature_title,
                              y_axis_label='Probability',
                              y_range=bokeh.models.Range1d(0, 1, bounds='auto')
                              );
    
    p.title.align='center';
    p.title.text_font_size=font_size;
    p.xaxis.major_label_text_font_size=font_size;
    p.xaxis.axis_label_text_font_size=font_size;
    p.yaxis.major_label_text_font_size=font_size;
    p.yaxis.axis_label_text_font_size=font_size;

    p = process_new_cdf(feature, feature_freq_dist_df, p);

    figs_list.append(p);


# Driver for analyzer.
def main():
    
    global args;
    global ds_df;
    global xlsfiles;
    
    args = process_args();
    print('');
    check_args();
    print('');
    echo_args();
    print('');
    start = datetime.datetime.now();

    ds_df = prune_records(ds_df);

    if (not ds_df.empty):
        
        pathstr, file_ext = os.path.splitext(args.data_store);
        dir_name = args.directory if args.directory else os.path.dirname(pathstr);
        filename = os.path.basename(pathstr);
        htmlfile = dir_name + '/' + filename + '.html';
        bokeh.plotting.output_file(htmlfile, title="Project Statistics");

        print("Identifying projects...");
        project_ids_df = get_project_ids_df(ds_df);
        print("Done.");
        
        features = ['total_num_commits',
                    'total_num_lines_changed',
                    'total_num_lines_inserted',
                    'total_num_lines_deleted',
                    'total_num_lines_modified'];
        
        dtdelta_labels = list();
        global dtdeltas;
        dtdeltas = ['d'];
        for dtdelta_code in dtdeltas:

            dtdelta_label = DTDELTA_LABELS[dtdelta_code];
            dtdelta_labels.append(dtdelta_label);

        FEATURES = features + dtdelta_labels;

        print("Building project summaries...");
        project_summaries_df = get_project_summaries_df(FEATURES, project_ids_df, ds_df);
        print("Done.");
        
        num_projects = project_summaries_df.shape[0];    
        
        print("Generating project statistics...");

        get_commit_patterns(project_ids_df, ds_df);

        num_features = len(FEATURES);

        for i in range(0, num_features):
            
            feature = FEATURES[i];
            
            process_distribution_figs(feature, project_summaries_df);
            
            feature_freq_dist_df = get_feature_freq_dist_df(feature, project_summaries_df);

            get_histogram(feature, feature_freq_dist_df);
            get_cdf(feature, feature_freq_dist_df);
            
            pathstr, file_ext = os.path.splitext(args.data_store);
            dir_name = args.directory if args.directory else os.path.dirname(pathstr);
            filename = os.path.basename(pathstr);
            xlsfile = dir_name + '/' + filename + '-' + feature + '.xlsx';
            sh.write_df_to_file(feature_freq_dist_df, feature, xlsfile);
            xlsfiles.append(xlsfile);
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


