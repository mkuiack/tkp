#!/usr/bin/python

import os
import time
import tkp_lib.database as db
import tkp_lib.dataset as d

starttime = time.time()

#basedir = '/home/bscheers/maps/wenss/'
#basedir = '/home/bscheers/genimages/random_sources3/'
#basedir = '/home/bscheers/selected_genimages/'
#basedir = '/home/bscheers/maps/cygx3_images/'
#basedir = '/home/bscheers/maps/cygx3_few_images/'
basedir = '/home/bscheers/maps/bower/'

imagesdir = basedir + 'fits/'

#logfile = basedir + 'log/proctimes.log'
#log = open(logfile, 'w')

files = os.listdir(imagesdir)
files.sort()
images = []
for file in files:
    images.append(imagesdir + file)

dataset = d.DataSet('Bower-VLA_D-Cellsize2.2-uncorr', images)
print dataset

conn = db.connection()
print conn

for img in dataset:
    imgstarttime = time.time()
    img.wcs.coordsys  = 'fk4'
    img.wcs.outputsys = 'fk5'
    results = img.sextract(det=7)
    imgendtime = time.time()
    imgelapsed = imgendtime - imgstarttime
    print "Image processing time %6.3f seconds" % (imgelapsed)
    dbstarttime = time.time()
    results.savetoDB(conn)
    dbendtime = time.time()
    dbelapsed = dbendtime - dbstarttime
    print "DB insertion time %6.3f seconds" % (dbelapsed)
    subtotelapsed = dbelapsed + imgelapsed
    print "Subtotal proc time %6.3f seconds" % (subtotelapsed)
    #row = str(seq_nr) + ';' + str(subtotelapsed) + ';' + str(dbelapsed) + ';' + str(imgelapsed) + '\n'
    #log.write(row)

endtime = time.time()
elapsed = endtime - starttime

log.close()
conn.close()

print "Total processing time %.3f seconds" % (elapsed)
