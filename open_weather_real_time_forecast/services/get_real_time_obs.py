import os
import re
import shutil
import datetime
import multiprocessing
from datetime import date, timedelta
from calendar import monthrange

from urllib.request import urlopen
from bs4 import BeautifulSoup
from tqdm.notebook import tqdm
import pandas as pd
import numpy as np

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt

from metar import Metar

import portolan

BASE_DIR = os.path.abspath(os.getcwd())