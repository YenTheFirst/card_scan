Card recognition and organization based on [opencv](opencv.willowgarage.com)

[demo video](http://youtu.be/ppNy9fdw91E)

This is a set of utilities to recognize and extract card images from a video feed, and then recognize those images against a known database.

**dependencies and setup:**
 * Python (tested and written with version 2.7)
 * The primary external dependency OpenCV(opencv.willowgarage.com), which unfortunately can't be installed through PIP at the moment.
    * I installed OpenCV and the Python bindings through Debian's package manager. Depending on your system, the install process may be different.
    * This is written and tested with OpenCV Version 2.3.1-7, per the Debian packages
 * The app also requires numpy and Flask (for the webapp verifier). These can be installed with `pip install -r requirements.txt`
 * For recognition, you'll need a downloaded copy of all the images you want to match against, in a folder structure that tags the images with a 'set' and 'name'.

---

**Non-computer dependencies:**
 * A computer-attached camera, such as a webcam, that is compatible with OpenCV. On Linux, any V4L compatible camera should work.
 * A scanning area. This consists of:
    1. A flat, blank, stable 'background' mat to scan on.
    1. A mounting area, so the camera can look down on the mat and the cards being scanned
    1. Appropriate lighting. It usually helps to have lighting coming from the side, to reduce specular highlights messing up image recognition.
    1. It also helps to have lighting coming from both sides, to reduce the effect of slightly curved cards throwing shadows that alter their rectangular shape in the camera's view.
 * An orginizational system to house the cards in afterwards. I'm using a set of numbered boxes, that each hold 60 cards, and tagging each scanned card with the box number that it's stored in.

---

**Walkthrough of scanning and recognition process**

*Scanning:*
  1. Set up the scanning area, with a camera attached to your computer.
  1. open a python shell
  1. `import cv`
  1. `import scan_card`
  1. create the opencv capture device with `cv.CreateCameraCapturei(<num>)`. On linux, if your camera is /dev/video0, you'll run `cam = cv.CreateCameraCapture(0)`, for example.
  1. create the output windows with `scan_card.setup_windows()`
    * they won't show up until the capture loop starts running.
  1. run `captures = scan_card.watch_for_card(<capture device>)`
    * while capturing, there are some keystrokes available:
    * you can middle-click a picture to delete that scan
    * you can press spacebar to rescan an image without removing it. This is useful when the program hasn't detected movement when it should have, or when you're scanning multiple of the same card.
    * you can press 'r' to 'rescan' the background. This is helpful when it's not detecting motion properly. Only press this when the scan area is empty, or it will mess up detection.
    * you can press 'escape' to exit the scan loop.
  1. After you're done (via pressing 'escape'), you can save the captures to a folder with `scan_card.save_captures(<boxnum>, <captures>`
  1. You can import that folder to an sqlite3 database with `scan_card.folder_to_db(<boxnum>)


*Matching:*
  1. You need to have a downloaded set of images to match against. In my case, I matched the [Cockatrice](http://cockatrice.de) folder structure, which is '/setabbrev/cardname.jpg'
  1. import the known images with `known = scan_card.load_sets(<base directory>, <list of set abbreviations>`
    * for example, this app has LIKELY_SETS, which is a list of the sets most of my cards come from.
  1. (optional) create a debug output window, with `cv.NamedWindow('debug')`
  1. run the matching process with `scan_card.match_db_cards(<known>)_`. Depending on the number of cards, this may take a few hours.
  1. Afterwards, you will likely need to verify the matches.

*Verification:*
  1. edit website.py with your base dir for downloaded images. (line 25)
  1. run `python website.py`
  1. open a webbrowser to [http://localhost:5000/verify_scans]
  1. visually scan over the pairs of scanned images on the left and matched images on the right. I recommend using tab to run through these.
  1. Where there's a discrepancy, type in the correct set name and card name. the 'match' image will automatically update.
  1. when you complete a page, press 'submit' to save any changes to the database, and mark all images on that page as 'verified'
  1. continue verifying pages (50 cards at a time), until all cards are verified.
    
