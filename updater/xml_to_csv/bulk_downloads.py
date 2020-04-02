from bs4 import BeautifulSoup
from urllib.request import urlretrieve
import requests
from zipfile import ZipFile
import os
import logging

from QA.xml_to_csv.DownloadTest import DownloadTest

logger = logging.getLogger("Bulk Downloads")


def get_zip_url_year(page_url):
    """
    Parse through each URL (for one year) to get the download links
    :param page_url: URL to parse through
    :return: List of download links
    """
    # open the link and parse through html tags
    page_open = requests.get(page_url)
    html_content = BeautifulSoup(page_open.content)

    # extract html elements with href tag
    href_tag = []
    for tag in html_content.find_all('a', href=True):
        if tag.text:
            href_tag.append(tag['href'])

    # keep only the links with .zip that are downloadable
    download_tag = [x for x in href_tag if '.zip' in x]
    download_url = []
    for tag in download_tag:
        download_url.append(page_url + '/' + tag)

    return download_url


def get_zip_url_all(page_url_lst):
    """

    :param page_url_lst:
    :return:
    """
    # get the downloadable zip file link for all the years
    zip_url_lst = []
    for url in page_url_lst:
        zip_url_lst += get_zip_url_year(url)

    return zip_url_lst


def get_date_url(zip_url_lst, start_date, end_date):
    # create a dictionary with date as key, download url as value
    time_url_dict = {}
    for url in zip_url_lst:
        # extract the time from url
        time = int('20' + url.split('/')[-1].split('.')[0][3:].split("_")[0])
        # write in to the dictionary
        time_url_dict[time] = url

    # compare the date given by the user to get a list of url that needs to be downloaded
    url_list = []
    for d in time_url_dict.keys():
        if d >= int(start_date) and d <= int(end_date):
            url_list.append(time_url_dict[d])

    return sorted(url_list)


def extract_file(download_url):
    """
    Download the .zip file from a url, unzip it, and delete the .zip file(keep unzip files)
    :param download_url:
    """
    # get the url to download to thew orking directory get the name of the file
    name = download_url.split('/')[-1]
    hdrs = urlretrieve(download_url, name)

    # unzip the file just downloaded
    zip_file = ZipFile(name)
    zip_file.extractall()
    zip_file.close()
    os.remove(name)


def begin_download(update_config):
    start_date = update_config['DATES']['START_DATE']
    end_date = update_config['DATES']['END_DATE']
    folder = '{working_folder}/raw_data'.format(working_folder=update_config['FOLDERS']['WORKING_FOLDER'])
    if not os.path.exists(folder):
        os.makedirs(folder)
    for date in [start_date, end_date]:
        if len(date) != 8:
            logger.debug(date)
            logger.debug(len(date))
            raise ValueError('Please input a date in the form of "YYYYMMDD"')
        # get the year and date (converted to int) of the date a user input
        date = int(date)
        if date < 20050101:
            raise ValueError('Please input a date that is later than 2005/01/01')
    start_year = int(start_date[0:4])
    end_year = int(end_date[0:4])
    # create a folder to save files
    os.chdir(folder)

    # start downloading
    logger.info("Starting downloading data...")

    # create a list of page URL's to parse through
    main_url = 'https://bulkdata.uspto.gov/data/patent/grant/redbook/fulltext/'
    page_url_lst = []

    # get a list of url that is after the specified year
    for i in range(start_year, end_year + 1):  # +1 because end is exclusive
        page_url_lst.append(main_url + str(i))

    # get all downloadable zip file link
    zip_url_lst = get_zip_url_all(page_url_lst)
    # get the urls that need to be downloaded
    urls_to_download = get_date_url(zip_url_lst, start_date, end_date)

    for url in urls_to_download:
        extract_file(url)

    logger.info("Download Finished")


def bulk_download(**kwargs):
    update_config = kwargs['config']

    begin_download(update_config)
    try:
        post_download(update_config)
    except AssertionError as e:
        raise AssertionError("Error when validating downloaded XMLs")


def post_download(update_config):
    qc_step = DownloadTest(update_config)
    qc_step.runTest(update_config)


if __name__ == '__main__':
    import configparser

    project_home = os.environ['PACKAGE_HOME']
    config = configparser.ConfigParser()
    config.read(project_home + '/config.ini')
    bulk_download(**{'config': config})
