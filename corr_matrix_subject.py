import sys,os,pandas,re
import pandas as pd
from os.path import join,getsize
from pandas import Series,DataFrame
import matplotlib.pyplot as plt
from sklearn import metrics
from plot_subject import read_subject_sizes
def get_files(path,template):
    '''
        Args:
            path: the path to find files in
            template: the template to match names
        Returns: the list of files matching template in path
    will combile tempalte into pattern. 
    
    '''
    matches = []
    pattern = re.compile(template)
    for root, dirs,filenames in os.walk(path):
        for name in filter(lambda name:pattern.match(name),filenames):
            matches.append(join(root,name))
    return matches

def is_sub_cluster(file_path,template = None):
    if template is None:
        template = '.+\d+_\d+\..+'
    pattern = re.compile(template)
    if pattern.match(file_path):
        return True
    else:
        return False
def get_cluster_name(file_path):
    '''
    we say main# is the main cluster number,
    we also say sub# is the sub cluster number, 
    returns: 
    main#_sub#_0-49 if sub# is present. 
    main#_0=499 if no sub#
    '''
    if is_sub_cluster(file_path):
        main_num = main_number(file_path)
        sub_nums = sub_numbers(file_path)
        return [sub_nums+'_'+str(item) for item in range(50)]
    else:
        main_num = main_number(file_path)
        return [main_num +'_'+str(item) for item in range(500)]

def sub_numbers(file_path):
    '''
    e.g.cluster_centers/cluster_centers_subject0_40.csv
    should return 40
    getting the cluster number
    Args:
        file_path: the path of file
    Returns: 
        String of cluster number if sub cluster
        None if not
    '''
    template = '(.*)(\d+_\d+)(.+)'
    pattern = re.compile(template)
    m = pattern.match(file_path)
    if m:
        cluster_number = m.groups()[-2]
        return cluster_number
    else:
        return None
def main_number(file_path):
    '''
    e.g. cluster_centers/cluster_centers_subject0_40.csv
    should return 0
    Args:
        file_path: the path of file
    Returns:
        String of main cluster number if sub cluster
        None if not
    '''
    template = '(.*)(\d+)(.+)'
    pattern = re.compile(template)
    m = pattern.match(file_path)
    if m:
        cluster_number = m.groups()[-2]
        return cluster_number
    else:
        return None

def read_file(file_path):
    '''
    read in a file and return a pandas dataframe. 
    Args:
        file_path: the string of file path
    '''
    data = pd.read_csv(file_path,header=None)
    return data

def read_files_center(file_paths):
    '''
    Args:
        file_paths: a list of string of file path. 
    Return:
        a pandas dataframe of all file_paths
    '''
    dfs = []
    for file_path in file_paths:
        data = read_file(file_path)
        #remove the last None because I put an extra ',' at the end of each line
        data = data[data.columns[:-1]]
        dfs.append(data)
    return pd.concat(dfs)
def read_files_max(file_paths):
    '''
    Args:
        file_paths: a list of string of file path. 
    Return:
        a pandas dataframe of all file_paths
    '''
    dfs = []
    for file_path in file_paths:
        data = pd.read_csv(file_path,header=None,index_col=0)
        if is_sub_cluster(file_path):
            prefix = sub_numbers(file_path)+'_' 
        else:
            prefix = main_number(file_path)+'_'
        data.index = prefix+data.index.astype(str)
        dfs.append(data)
    return pd.concat(dfs)

if __name__=='__main__':
    if len(sys.argv)<4:
        print 'ERROR: no subject number supplied'
        print 'Usage: python corr_matrix_subject.py subject# cluster_center_path max_dis_path'
        print 'e.g. python corr_matrix_subject.py 0 cluster_centers/ max_point_distance/'
        sys.exit(1)
    subject = sys.argv[1]
    path = sys.argv[2]
    print 'getting correlation matrix for subject',subject
    template = 'cluster_centers_subject'+str(subject)+'.*csv'
    file_names = get_files(path,template)
    data = read_files_center(file_names) 
    #obtain 1000*1000 cluster
    result = metrics.pairwise.pairwise_distances(data)
    cluster_names = []
    for file_name in file_names:
        cluster_names.extend(get_cluster_name(file_name))
    template_max = str(subject)+'.*csv'
    file_names_max = get_files(sys.argv[3],template_max)
    data_max = read_files_max(file_names_max)
    print file_names_max
    for i in range(len(result)):
        for j in range(len(result[0])):
            result[i][j]+=data_max.ix[cluster_names[i]]
            result[i][j]+=data_max.ix[cluster_names[j]]
    plt.matshow(result)
    plt.colorbar()
    plt.savefig('test'+str(subject)+'.png')
