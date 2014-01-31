Card recognition and organization based on [opencv](http://opencv.org/)

[demo video](http://youtu.be/ppNy9fdw91E)

This is a set of utilities to recognize and extract card images from a video feed, and then recognize those images against a known database.

**Dependencies and Setup**

python 2.7, numpy, Flask, SQLAlchemy, Elixir
<pre>
sudo apt-get install python-dev
sudo pip install -r requirements.txt
</pre>
[OpenCV](http://opencv.org/) 2.3.1-7
<pre>sudo apt-get install python-opencv</pre>

* MTG Set Card Images ([GathererDownloader Instructions](https://github.com/chrismeyersfsu/card_scan/wiki/Gatherer-Downloader))
* webcam
* white printer paper

**Configure**

<a href="config.py">config.py</a>

<code>db_file="inventory.sqlite3"</code>

<code>cards_file="cards.xml"</code> card listing obtained from [GathererDownloader](https://github.com/chrismeyersfsu/card_scan/wiki/Gatherer-Downloader)

<code>basic_magic_set_dir="cards/"</code> card images obtained from [GathererDownloader](https://github.com/chrismeyersfsu/card_scan/wiki/Gatherer-Downloader)

**Running**

***1. Scan***
<pre>python -m utils.run_scan</pre>
<br />

<center>

| Key                  | Function     |
|:--------------------:|--------------|
| <i>middle mouse wheel</i> | delete scan  |
| <i>space</i>              | rescan image |
| <i>r</i>                  | rescan background |
| <i>escape</i>             | finish scanning |

</center>
<br />

***2. Match***

Requires an image set to match against ([GathererDownloader Instructions](https://github.com/chrismeyersfsu/card_scan/wiki/Gatherer-Downloader))
<pre>python -m utils.run_match</pre>

***3. Verify***

Verification allows you to manually label any cards the matching process could not recognize, or was uncertain about whether its recognition was correct.
<pre>python website.py</pre>
[http://localhost:5000/verify_scans](http://localhost:5000/verify_scans)

**Scanning Notes**

It also helps to have lighting coming from both sides, to reduce the effect of slightly curved cards throwing shadows that alter their rectangular shape in the camera's view.
 
---

***Licensing***

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

