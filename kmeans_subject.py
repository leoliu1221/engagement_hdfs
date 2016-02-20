from pyspark import SparkContext
import os,itertools,time,math
import numpy as np
from pyspark.mllib.clustering import KMeans, KMeansModel
from numpy import array
from math import sqrt
import pickle
subject = 0

# Evaluate clustering by computing Within Set Sum of Squared Errors
def error(point, clusters):
    center = clusters.centers[clusters.predict(point)]
    return sqrt(sum([x**2 for x in (point - center)]))

def save_cluster_centers(centers,file_name):
    '''
    remove file_name file, create new file_name file, write item[0],item[1] for top_sizes in each line of file_name
    Args:
        top_sizes: list of list of feature items. 
        file_name: String of file_name output
    Returns:
        None
    '''
    os.system('rm -rf '+file_name)

    with open(file_name,'w') as f:
        for item in centers:
            for item2 in item:
                f.write(str(item2))
                f.write(',')
            f.write('\n')

def save_cluster_sizes(top_sizes,file_name):
    '''
    remove file_name file, create new file_name file, write item[0],item[1] for top_sizes in each line of file_name
    Args:
        top_sizes: list of 2tuples. 
        file_name: String of file_name output
    Returns:
        None
    '''
    os.system('rm -rf '+file_name)

    with open(file_name,'w') as f:
        for item in top_sizes:
            f.write(str(item[0]))
            f.write(',')
            f.write(str(item[1]))
            f.write('\n')

def xyz_feature(xyz_value):
    xyz_key = xyz_value[0]
    xyz_dict = xyz_value[1]
    features = [np.array(xyz_dict[key].split(',')).astype(float) for key in sorted(xyz_dict.keys())]
    merged = list(itertools.chain.from_iterable(features))
    return (xyz_key,merged) 

def xyz_subject_feature(xyz_value,subject = subject):
    '''
    Used for reducing
    Can be improved.
    Args:
        xyz_value: a 2tuple (xyz_key,xyz_dict)
        subject: the subject number to keep
    Returns:
        if subject in value, then (xyz_key, numpyArray of given subject)
        else (xyz_key, first value in xyz_dict.values())
    '''
    xyz_key = xyz_value[0]
    xyz_dict = xyz_value[1]
    if str(subject) in xyz_dict.keys():
        return (xyz_key,np.array(xyz_dict[str(subject)].split(',')).astype(float))
    else:
        return (xyz_key,np.array(xyz_dict.values()[0].split(',')).astype(float))

def value_pairs(line):
    '''
    get 'x,y,z' => values key=> value pairs
    Args:
        line is string of a line
        x;y;z;t0,t1,t2,...,tn
    '''
    values = line.split(';')
    #so now the first 3 are x,y and z.
    x=  values[0]
    y = values[1]
    z = values[2]
    subject = values[3]
    timeseries = values[4]
    return ((x,y,z),{subject:timeseries})

def xyz_group(xyz1,xyz2,subject=subject):
    '''
    Update xyz1 and xyz2 if they have the same xyz_key
    Args:
        xyz1: a dictionary xyz_dict for key1
        xyz2: another dictionary xyz_dict for key1
    '''
    full = xyz1
    full.update(xyz2)
    return full

def print_rdd(rdd):
    '''
    Utility to print a rdd
    '''
    for x in rdd.collect():
        print x

def get_eud(values):
    pair1 = values[0]
    pair2 = values[1]
    xyz1 = pair1[0]
    xyz2 = pair2[0]
    v1 = [float(item) for item in pair1[1].split(',')]
    v2 = [float(item) for item in pair2[1].split(',')]
    result = sum([(v1[i]-v2[i])**2 for i in range(len(v1))])
    return ((xyz1,xyz2),math.sqrt(result))

def filter_0(line):
    array = [float(item) for item in line.split(';')[3]]
    return sum(array)!=0

time_now = time.time()
sc = SparkContext()
hdfsPrefix = 'hdfs://wolf.iems.northwestern.edu/user/huser54/'
fileName1 = 'engagement/'
fileName2 = 'engagementsample/'
lines = sc.textFile(hdfsPrefix+fileName2)
#map the values to xyz string -> dictionary of subjects with time series. 
values = lines.map(value_pairs)
print 'values obtained'
#print values.first()
#print 'value obtain time:',time.time()-time_now
time_old = time.time()

#group by key. Using reduce. Because groupby is not recommended in spark documentation
groups = values.reduceByKey(xyz_group)
print 'groups finished'
#print groups.first()
#print 'group obtain time:',time.time()-time_now
time_now = time.time()

#map the groups to xyz -> array, where array is 0-22 subject points. 
feature_groups = groups.map(xyz_subject_feature)
print 'feature group'
#print feature_groups.first()
#print 'feature obtain time:',time.time()-time_now
time_now = time.time()

parsedData = feature_groups.map(lambda x:x[1])
print 'parsed data'
#print parsedData.first()
#print 'parsed data obtain time:',time.time()-time_now
time_now = time.time()
#now we have xyz -> group of features
#and we are ready to cluster. 
# Build the model (cluster the data)
#document states:
#classmethod train(rdd, k, maxIterations=100, runs=1, initializationMode='k-means||', seed=None, initializationSteps=5, epsilon=0.0001,initialModel=None)
clusters = KMeans.train(parsedData, 500, maxIterations=100,runs=10, initializationMode="k-means||")
print 'cluster obtain time:',time.time()-time_now
time_now = time.time()

WSSSE = parsedData.map(lambda point: error(point,clusters)).reduce(lambda x, y: x + y)
os.system('rm -rf WSSE_subject'+str(subject)+'.dat')
with open('WSSE_subject'+str(subject)+'.dat','w') as f:
    f.write(str(WSSSE))

time_now = time.time()

#cluter centers after calculating kmeans clustering
#clusterCenters = sc.parallelize(clusters.clusterCenters)

print 'clearing hdfs system'
os.system('hdfs dfs -rm -r -f '+hdfsPrefix+'clusterCenters')
cluster_ind = parsedData.map(lambda point:clusters.predict(point))
cluster_ind.collect()
cluster_sizes = cluster_ind.countByValue().items()

save_cluster_sizes(cluster_sizes,'cluster_sizes_subject'+str(subject)+'.csv')
save_cluster_centers(clusters.centers,'cluster_centers_subject'+str(subject)+'.csv')

#get top clusters to split again
top_clusters = [item[0] for item in sorted(cluster_sizes,key=lambda x:x[1],reverse=True)[0:10]]

#now we got the top 10 clusters. For each cluster, we will split 50 again. 
for top_cluster in top_clusters:
    top_data = parsedData.filter(lambda point:clusters.predict(point)==top_cluster)
    #now temp_data has all filtered by top_cluster. 
    #Now we are going to cluster it. 
    top_model = KMeans.train(top_data, 50, maxIterations=100,runs=10, initializationMode="k-means||")
    top_wsse = top_data.map(lambda point: error(point,top_model)).reduce(lambda x, y: x + y)
    top_ind = top_data.map(lambda point:clusters.predict(point))
    top_ind.collect()
    top_sizes = top_ind.countByValue().items()

    save_cluster_sizes(top_sizes,'cluster_sizes_subject'+str(subject)+'_'+str(top_cluster)+'.csv')
    save_cluster_centers(top_model.centers,'cluster_centers_subject'+str(subject)+'_'+str(top_cluster)+'.csv')
    print 'finished top cluster',top_cluster

    

#save as text file to clusterCenters in hdfs
print 'save cluster center',time.time()-time_now

print 'wssse obtain time:',time.time()-time_old
print("Within Set Sum of Squared Error = " + str(WSSSE))