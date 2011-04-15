#!/usr/bin/python

import os, time
from itertools import count
import tkp_lib.database as db
import tkp_lib.dataset as d
import tkp_lib.settings as s
from tkp_lib import image, accessors, containers

starttime = time.time()

basedir = '/home/bscheers/maps/wenss/'
imagesdir = basedir + 'fits/'

logtime = time.strftime("%Y-%m-%d-%H:%M:%S")
logfile = basedir + 'log/proctimes' + logtime + '.log'
log = open(logfile, 'w')
print "logfile: ", logfile

#my_images = (imagesdir + "WN30143H",
#    imagesdir + "WN30218H",
#    imagesdir + "WN30224H"
#)
#dataset = d.DataSet("my dataset", my_images)

description = 'Testing pipeline_develop assoc; WENSS det=80'
dataset = d.DataSet(description)
print dataset.id
#dataset = d.DataSet(description, images)

#for nr, im in zip(count(), dataset):
#    print "nr = ", nr, "; dsid = ", dataset._id, "; imid = ", im._id

#"""
log.write(description + '\n')
row = 'database type: ' + s.database_type + '\n'
log.write(row)
row = 'image; ' + 'nsources; ' + 'imgelapsed; ' + 'dbelapsed; ' + 'subtotal; \n'
log.write(row)
row = '------------------------------------------------------ \n'
log.write(row)
#print "dataset id: ", dataset.id

conn = db.connection()
#print conn

i = 0
files = os.listdir(imagesdir)
files.sort()
for file in files:
    if (file == 'WN30218H' or file == 'WN30224H' or file == 'WN30230H'):
    #if (file == 'WN35216H' or file == 'WN35222H'):
    #if (file == 'WN30143H'):
        print "i: ", i, ", file: ", file
        #dataset.append(imagesdir + file)
        imgstarttime = time.time()
        my_fitsfile = accessors.FitsFile(imagesdir + file)
        my_image = image.ImageData(my_fitsfile, dataset = dataset)
        print "imageid:", my_image.id[0]
        my_image.wcs.coordsys  = 'fk4' 
        my_image.wcs.outputsys = 'fk5'
        results = my_image.sextract(det=80)
        imgendtime = time.time()
        nsources = len(results)
        imgelapsed = imgendtime - imgstarttime
        print "Image processing time %6.3f seconds" % (imgelapsed)
        dbstarttime = time.time()
        results.savetoDB(conn)
        #results.assocDB(conn)
        dbendtime = time.time()
        dbelapsed = dbendtime - dbstarttime
        print "DB insertion time %6.3f seconds" % (dbelapsed)
        subtotelapsed = dbelapsed + imgelapsed
        print "Subtotal proc time for this image: %6.3f seconds" % (subtotelapsed)
        row = str(i) + ';' + str(nsources) + ';' + str(imgelapsed) + ';' + str(dbelapsed) + ';' + str(subtotelapsed) + '\n'
        log.write(row)
        my_image.clearcache()
        i = i + 1

endtime = time.time()
elapsed = endtime - starttime

log.close()
conn.close()

print "Total processing time for dataset: %.3f seconds" % (elapsed)
#"""

