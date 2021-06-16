# Python script to scan directory structure of StereoVision system data files.
# The StereoVision system was designed and built by Marine Situ for the ORPC
# Igiugig project.  Two stereo pairs of cameras were installed on a RivGen 
# instream turbine and the device was deployed in Kvichak river in October 2019.

# The directory structure is as follows:
# day
#  |--time (every few minutes)
#      |--Camera Pair 1 Settings.txt
#      |--Camera Pair 2 Settings.txt
#      |--Camera X (4)
#          |--Timestamps.txt
#          |--YYYY_MM_DD_hh_mm_ss.ff.jpg (images)
#

# The settings files can be used to get the frame rate.  If the frame rate is 0,
# then the camera pair was not recording.
# Example settings file:
'''
8/1/2019, 9:54:05 AM

Auto-Frame Rate Enabled: 0
Frame Rate 1 [Hz]: 10.00
Frame Rate 2 [Hz]: 10.00

Auto-Exposure Enabled: 1
Exposure 1 [ms]: 3.28
Exposure 2 [ms]: 3.35

Auto-Gain Enabled: 1
Gain 1: 0.00
Gain 2: 0.00
Gamma: 0.80
'''

import os
import cv2
import glob
import ffmpeg
import csv
import sys
import time
import subprocess
import shutil
import traceback

from eyesea_db import *

# Parse the settings file and return:
# dt: date time
# fps: frames per second, 0 -> camera pair was not enabled, 1 -> auto 
# exp: exposure, 1 -> auto
# gain: gain, 1 -> auto
def parse_camera_settings(timedir):
    # TODO: Actually parse the files
    files = ["Camera Pair 1 Settings.txt", "Camera Pair 2 Settings.txt"]
    dt = [0, 0, 0, 0]
    fps = [10.0, 10.0, 10.0, 10.0]
    exp = [1, 1, 1, 1]
    gain = [1, 1, 1, 1]
    return dt, fps, exp, gain
# parse_settings()

# make an mp4 video out of image files
# using python bindings for ffmpeg:
# https://github.com/kkroening/ffmpeg-python/tree/master/examples
# ffmpeg tuning:
# https://trac.ffmpeg.org/wiki/Encode/H.264
def make_movie(imgpath,fps,outfile):
    filenames = sorted(glob.glob(os.path.join(imgpath,'*.jpg')))

    spf = 1 / fps

    frames_filename = outfile + '-frames.txt'
    try:
        with open(frames_filename, 'w') as f:
            for filename in filenames:
                f.write("file '{}'\n".format(filename))
                f.write("duration {}\n".format(spf))
            if len(filenames) > 0:
                f.write("file '{}'\n".format(filenames[-1]))
        (
            ffmpeg
            .input(frames_filename, format='concat', safe=0, r=fps)
            .output(outfile 
                ,vcodec='libx264'
                ,crf=17
                ,pix_fmt='yuv420p'
                )
            .overwrite_output()
            .run()
        )
    except Exception as e:
        print(exception_to_string(e))
        print("Unexpected error:", sys.exc_info()[0])
    finally:
        if os.path.exists(frames_filename):
            os.remove(frames_filename)

def exception_to_string(excp):
   stack = traceback.extract_stack()[:-3] + traceback.extract_tb(excp.__traceback__)  # add limit=?? 
   pretty = traceback.format_list(stack)
   return ''.join(pretty) + '\n  {} {}'.format(excp.__class__,excp)

# make_movie()

# TODO: if database already exists, then don't create tables

def init_database(dbpath, algdir, algname):
    db.init(dbpath)
    if not os.path.exists(dbpath): 
        print('Creating new database ' + os.path.basename(dbpath))
        create_tables()
    try:
        method = analysis_method.select().where(
            analysis_method.description.contains(algname)
            ).dicts().get()
    except DoesNotExist:
        print("Adding analysis method {} to database".format(algname))
        algjsonfile = os.path.join(algdir, algname + '.json')
        fdict = json.loads(open(algjsonfile).read())
        fjson = json.dumps(fdict)  # normalize json
        method = analysis_method.select().where(
            analysis_method.mid==analysis_method.insert(
                creation_date = int(time.time())
                , description = fdict['name']
                , parameters = fjson
                , automated = True
                , path = algdir 
                ).execute()).dicts().get()
    return method

if __name__ == "__main__":

    from datetime import datetime
    import configargparse

    

    print("")
    print("Starting...")

    # start the clock
    start_time = datetime.now()

    # Get runtime argsif args.xml: api.put_results_xml(idx, detections)
    p = configargparse.ArgParser(default_config_files=['./.stereovision', '~/.stereovision'])
    p.add('-c', required=False, is_config_file=True, help='config file path')
    # options that start with '--' can be set in the config file
    p.add('-d', '--datadir', required=True, help='root of data directories')  
    p.add('-p', '--prefix', required=False, help='prefix for database files', default='stereovision')  
    p.add('-f', help='force processing if data was already processed', action='store_true')
    #p.add('-v', help='verbose', action='store_true')
    #p.add('-d', '--dbsnp', help='known variants .vcf', env_var='DBSNP_PATH')  
    #p.add('vcf', nargs='+', help='variant file(s)')
    options = p.parse_args()
    print(p.format_values()) 

    rootdir = options.datadir
    force = options.f

    settings = json.loads(open('eyesea_settings.json').read())
    # TODO: get this from args and update settings with new database
    dbdir = os.path.abspath(os.path.expandvars(settings['database_storage']))
    if not os.path.isdir(dbdir):
        os.makedirs(dbdir)

    vdir = os.path.abspath(os.path.expandvars(settings['video_storage']))
    if not os.path.isdir(vdir):
        os.makedirs(vdir)

    tmp = os.path.abspath(os.path.expandvars(settings['temporary_storage']))
    if not os.path.isdir(tmp):
        os.makedirs(tmp)

    cache = os.path.abspath(os.path.expandvars(settings['cache']))
    if not os.path.isdir(cache):
        os.makedirs(cache)

    voverlay_dir = os.path.abspath(os.path.expandvars(settings['video_overlay_storage']))
    if not os.path.isdir(voverlay_dir):
        os.makedirs(voverlay_dir)

    csv_dir = os.path.abspath(os.path.expandvars(settings['csv_storage']))
    if not os.path.isdir(csv_dir):
        os.makedirs(csv_dir)

    algdir = os.path.abspath(os.path.expandvars(settings['algorithms']))
    if not os.path.isdir(algdir):
        print('invalid algorithm dir: ' + algdir)
        exit(0)
    print('Algorithm dir is ' + algdir)

    # get analysis method to use
    # TODO: get this from args
    algname = 'bgMOG2'
    # cd to algorithm dir
    working_dir = os.getcwd()
    os.chdir(algdir)

    # TODO: resest these for each day
    #  keep total counts for stats
    nsec = 0
    nbytes = 0
    nvideos = 0
    nminutes = 0


    # get list of day directories
    daydirs = glob.glob(os.path.join(rootdir,'????_??_??'))
    if len(daydirs) == 0:
        timedirs = glob.glob(os.path.join(rootdir,'????_??_?? ??_??_??'))
        if len(timedirs) > 0:
            daydirs = [rootdir]
            
    print("Found {} days".format(len(daydirs)))
    for day in daydirs:
        print(day)
        dbpath = os.path.join(dbdir, options.prefix + '-' + os.path.basename(day) + '.db')
        print(dbpath)
        # open or create new database
        method = init_database(dbpath, algdir, algname)
        mid = method['mid']
        base_args = json.loads(method['parameters'])
        script = '{p}/{f}'.format(p=method['path'] if method['path'] else algdir, f=base_args['script'])

        # get list of time directories
        timedirs = glob.glob(os.path.join(day,'????_??_?? ??_??_??'))
        print("Found {} times".format(len(timedirs)))
        video_files = []
        video_fps = []
        video_dur = []
        analysis_proc = []
        analysis_results = []
        image_paths = []

        for t in timedirs:
            print(t)
            # read settings
            dt, fps, exp, gain = parse_camera_settings(t)

            # if there's data
            for cam in range(1,5):
                imgpath = os.path.join(t,'Camera {:d}'.format(cam))
                imgs = glob.glob(os.path.join(imgpath,'*.jpg'))
                print("Camera {:d} has {:d} images".format(cam, len(imgs)))
                if len(imgs) > 0:
                    vidfile = os.path.join(vdir, os.path.basename(t) + '_Cam{:d}.mp4'.format(cam))

                    csv_filename = os.path.splitext(os.path.basename(vidfile))[0] + '.csv'
                    csv_filepath = os.path.join(csv_dir, csv_filename)

                    if os.path.exists(csv_filepath) and not force: continue
                    if not os.path.exists(csv_filepath):
                        print("Making movie {}".format(vidfile))
                        make_movie(imgpath,fps[cam-1],vidfile)
                    thumbfile = os.path.join(cache, os.path.splitext(os.path.basename(vidfile))[0] + '.jpg')
                    shutil.copyfile(imgs[2], thumbfile)

                    # store movie path for ingest
                    video_files.append(vidfile)
                    video_fps.append(fps[cam-1])
                    video_dur.append(len(imgs) / fps[cam-1])
                    nsec += len(imgs) / fps[cam-1]
                    # process data with algorithm
                    print("Finding fish... ")
                    outfile = os.path.join(tmp, os.path.basename(t) + '_Cam{:d}.json'.format(cam))
                    args = ['python', script, imgpath, outfile]
                    p = subprocess.run(args)
                    analysis_proc.append(p)
                    analysis_results.append(outfile)
                    image_paths.append(imgpath)

        # ingest data into EyeSea database
        for vf,fr,dur,p,res,imgpath in zip(video_files,video_fps,video_dur,analysis_proc,analysis_results, image_paths):
            print("Ingesting {} into EyeSea database".format(os.path.basename(vf)))
            data = video.select().where(
                video.vid==video.insert(
                    filename = vf
                    , duration = dur
                    , description = os.path.splitext(os.path.basename(vf))[0]
                    , fps = fr
                    , creation_date = int(time.time())
                    , width = 0
                    , height = 0
                    , variable_framerate = False
                    , uri = 'file://' + vf
                    ).execute()).dicts().get()
            vid = data['vid']
            results = ''
            status = 'FAILED'

            csv_filename = os.path.splitext(os.path.basename(vf))[0] + '.csv'
            csv_filepath = os.path.join(csv_dir, csv_filename)

            detections_file = open(csv_filepath, newline='', mode='w')
            csv_writer = csv.writer(detections_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)

            csv_writer.writerow(['time', 'x', 'y', 'w', 'h', 'method'])
            
            os.makedirs(os.path.join(tmp, os.path.basename(vf)), exist_ok=True)

            if p.returncode == 0:
                print('    got results')
                status = 'FINISHED'
                with open(res) as f:
                    output = json.loads(f.read())['frames']
                    results = json.dumps(output, separators=(',', ':'))
                
                sorted_output = sorted(output, key=lambda x: x["frameindex"])
                filenames = sorted(glob.glob(os.path.join(imgpath,'*.jpg')))

                for out_row in sorted_output:
                    frame_num  = out_row["frameindex"]
                    detections = out_row['detections']

                    image = cv2.imread(filenames[frame_num])
                    for det in detections:
                        x1, y1, x2, y2 = det["x1"], det["y1"], det["x2"], det["y2"]

                        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 0, 255), 1)

                        timestamp = time.strftime('%H:%M:%S', time.gmtime(frame_num/fr))
                        timestamp += "{:.6f}".format(frame_num/fr % 1)[1:]
                        csv_writer.writerow([timestamp, x1, y1, x2 - x1, y2 - y1, algname])
                    cv2.imwrite(os.path.join(tmp, os.path.basename(vf), os.path.basename(filenames[frame_num])), image)

            detections_file.close()
            
            make_movie(
                os.path.join(tmp, os.path.basename(vf)),
                fr,
                os.path.join(voverlay_dir, os.path.basename(vf))
            )
            shutil.rmtree(os.path.join(tmp, os.path.basename(vf)))

            data = analysis.select().where(
                analysis.aid==analysis.insert(
                    mid = mid
                    , vid = vid
                    , status = status
                    , parameters = ''
                    , results = results
                    ).execute()).dicts().get()
        db.close()
        nvideos += len(video_files)

    os.chdir(working_dir)



    # get elapsed time
    time_elapsed = datetime.now() - start_time
    print("")
    print("Data Summary")
    print("{:d} videos".format(nvideos))
    print("{:.1f} minutes of video".format(nsec/60.0))
    #print("{:.3f} Mb of data".format(nbytes/1e6))
    print("")
    print('Elapsed time (hh:mm:ss.ms): {}'.format(time_elapsed))
    print(" ")

