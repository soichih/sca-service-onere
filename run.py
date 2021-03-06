#!/bin/env python
import os
import json
import sys
import glob
import errno
import shutil
import base64

#karst only
import requests
import magic

#load config.json
config_json=open("config.json").read()
config=json.loads(config_json)

jwt=config["jwt"] #jwt used to register new data to onere api
onere_api=config["onere_api"] #url for onere api

#directory where we store datasets. 
if "DATASET_DIR" in os.environ:
    dataset_dir=os.environ["DATASET_DIR"]
else:
    dataset_dir="/N/dc2/projects/lifebid/onere/datasets"
print "using dataset_dir:",dataset_dir

def import_file(config):
    print "importing file to onere dataset archive"

    #pull config params
    path=config["path"]
    filename=os.path.basename(path)
    dataset_id=config["dataset_id"] #dataset id to use to store this file 

    #get file stats (file type, etc..)
    filesize = os.path.getsize(path)
    filedesc = magic.from_file(path)
    filemime = magic.from_file(path, mime=True)

    #run validation tools based on file type
    #TODO..


    ###################################################################################################
    # everything above will probably removed from this service (or not implemeneted)
    # sca-service-onere should be responsible for moving data in/out of dataset

    #make sure datasets/:id directory exists
    dest_dir=dataset_dir+"/"+dataset_id
    try:
        os.makedirs(dest_dir)
    except OSError as exc: 
        if exc.errno == errno.EEXIST and os.path.isdir(dest_dir):
            pass
        else:
            raise

    #make sure desintation file doesn't already exists
    #TODO

    #copy file to dataset directory
    shutil.copy(path, dest_dir+"/"+filename)

    #make sure file is properly copied over (check size?)
    #TODO

    #(probably) change permission to read only so that sca/resource api can't easily delete / update the file
    #(I need to implement some capability to disable modification completely..)

    #get the current dataset info
    headers = {
        'Content-type': 'application/json',
        'Authorization': 'Bearer '+jwt,
    }
    find_json=json.dumps({"_id":dataset_id})
    response = requests.get(onere_api+"/dataset?find="+find_json+"&select=config", headers=headers)
    if response.status_code == 200:
        resobj = json.loads(response.content)
        dataset = resobj["datasets"][0]
        if not "config" in dataset:
            dataset["config"] = {}
        config = dataset["config"] 
        if not "files" in config:
            config["files"] = []
        files = config["files"] 

        #TODO - should I look for duplicate filenames?
        #if I check duplicate file above, such check shouldn'b be necessary

        files.append({
            'filename': filename,
            'size': filesize,

            'desc': filedesc,
            'mime': filemime,
            'dir': dest_dir, #to make it easier to access the file via sca-wf/download
        })
    else:
        print "failed to load dataset:",dataset_id
        sys.exit(1)

    #register to onere API
    dataset_json=json.dumps(dataset)
    response = requests.put(onere_api+"/dataset/"+dataset_id, data=dataset_json, headers=headers)
    print response

    #generate empty products.json
    with open('products.json', 'w') as out:
        #json.dump([{"type": "nifti", "files": niifiles}], out)
        json.dump([], out)

def export_file(config):
    print "exporting from onere dataset archive (just create symlink)"

    datasets=config["datasets"] 
    for dataset in datasets:
        src = dataset_dir+"/"+dataset["id"]
        dest = dataset["name"]
        try:
            os.symlink(src, dest)
        except OSError, e:
            if e.errno == errno.EEXIST:
                os.remove(dataset["name"])
                os.symlink(src, dest)

        #TODO - maybe I should increment the export count on onere api

    with open('products.json', 'w') as out:
        json.dump([{"type":"onere/dataset", "datasets":datasets}], out)

if "import" in config:
    import_file(config["import"])

if "export" in config:
    export_file(config["export"])
