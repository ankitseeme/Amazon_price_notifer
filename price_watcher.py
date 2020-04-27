#!/usr/bin/env python3

"""Price Watcher for Amazon.in"""

import os
import sys
from time import strftime
from random import shuffle, randint
import subprocess as s
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests
from lxml.html import fromstring
from bs4 import BeautifulSoup
from colorama import Fore, Style


START_TIME = strftime("%Y-%m-%d %H:%M:%S")

MAIL_FROM = "ankitseeme@gmail.com"
SUCCESS_MAIL_TO = ["ankitseeme@gmail.com", "ankitseeme@outlook.com"]
FAILURE_MAIL_TO = ["ankitseeme@gmail.com"]


def clear_screen():
    """Clear Terminal Screen"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_green_bright(msg, end=""):
    """Print Text in Green Color"""
    print(Fore.LIGHTGREEN_EX + Style.BRIGHT + msg + Style.RESET_ALL, end)


def print_red_bright(msg, end=""):
    """Print Text in Red Color"""
    print(Fore.RED + Style.BRIGHT + msg + Style.RESET_ALL, end)


def print_blue_bright(msg, end=""):
    """Print Text in Blue Color"""
    print(Fore.BLUE + Style.BRIGHT + msg + Style.RESET_ALL, end)


def print_new_line():
    """Print New Line"""
    print("")


class AccessError(Exception):
    """Exception for URL Access Error"""


class NoPriceError(Exception):
    """Exception for No Price on the fetched Page"""


def get_config(config_file_name):
    """Extract Credentials for EMAIL"""
    try:
        with open(os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])),
                               config_file_name), 'r') as u_f:
            data = json.load(u_f)

        return data["FILE_NAME"], data["LOG_FILE_NAME"], data["MAIL_CREDENTIALS_FILE"],\
               data["CHECK_LAST_N_LINES"]
    except Exception as error:
        print(error)
        system_exit_error("ReadConfigError")



def get_proxies():
    """Getting Proxy details for uninterrupted access"""
    url = 'https://www.socks-proxy.net/'
    try:
        response = requests.get(url)
        parser = fromstring(response.text)
        proxies = set()
        starting_point = randint(1, 70)
        total_range = randint(10, 20)
        for i in parser.xpath('//tbody/tr')[starting_point:starting_point + total_range]:
            if i.xpath('.//td[7]/text()')[0] == "Yes":
                #Grabbing IP and corresponding PORT
                proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
                proxies.add(proxy)
    except Exception as error:
        print(error)
        print_red_bright("Encountered some issue with proxies... Please check")
        system_exit_error("ProxyError")
    return proxies


def get_urls(url_file_name):
    """Get URls from the input file"""
    urls = {}
    commented_lines = []
    try:
        with open(os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])),
                               url_file_name), 'r') as u_f:
            for line in u_f:
                if (line.find('www.amazon.in') != -1 and not line.startswith("#")):
                    url = line.split('|')[0]
                    if len(line.split('|')) == 2:
                        previous_price = line.split('|')[1]
                        urls[url] = previous_price
                    else:
                        urls[url] = sys.maxsize
                elif line.startswith("#") and len(line) > 1:
                    commented_lines.append(line)
    except Exception as error:
        print(error)
        print_red_bright("Encountered some issue with input file... Please check")
        system_exit_error("InputFileError")
    print("Total Watched Products = " + str(len(urls)))
    return urls, commented_lines


def check_robot_output(html):
    """Check if Amazon is returning Automated Robot Check Reply"""
    bsobj = BeautifulSoup(html.text, 'lxml')
    robot_status = 0
    try:
        robot_text = bsobj.findAll('div', {'class':'a-box-inner'})[0].p.text
    except Exception as error:
        print(error)
    else:
        if robot_text.count("Sorry") == 1:
            robot_status = -1
        else:
            robot_status = 0
    return robot_status


def get_html(url, proxies):
    """Fetch Page from the given url"""
    proxies = list(proxies)
    shuffle(proxies)
    for proxy in proxies:
        try:
            #print_blue_bright("Trying for proxy " + proxy)
            html = requests.get(url, proxies={"http":proxy, "https":proxy}, headers=
                                {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64;x64) '\
                                'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113'\
                                ' Safari/537.36'}, timeout=10)
        except Exception as error:
            print(error)
        else:
            if html.status_code == 200 and check_robot_output(html) == 0:
                return html
    try:
        html = requests.get(url, headers=
                            {'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64;x64) '\
                            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113'\
                            ' Safari/537.36'}, timeout=10)
        if html.status_code == 200 and check_robot_output(html) == 0:
            return html
    except Exception as error:
        print(error)
        print_red_bright("Unable to access the page with URl : ")
        print_blue_bright(url.strip())
    return -1



def extract(url, html):
    """Get Item Description and Price"""
    bsobj = BeautifulSoup(html.text, 'lxml')
    try:
        desc = bsobj.find('span', {'id':'productTitle'}).text.strip()
    except Exception as error:
        print(error)
        print_red_bright("We ran into some trouble... Please try again")
        return -1, -1
    try:
        if bsobj.find('span', {'id':'priceblock_dealprice'}):
            price = [i for i in bsobj.find('span', {'id':'priceblock_dealprice'}).text
                     if i.isdigit() or i == '.']
            price = float(''.join(price))
        elif bsobj.find('span', {'id':'priceblock_ourprice'}):
            price = [i for i in bsobj.find('span', {'id':'priceblock_ourprice'}).text
                     if i.isdigit() or i == '.']
            price = float(''.join(price))
        else:
            raise NoPriceError
    except NoPriceError:
        print(url)
        print_red_bright("Can't find price... Please try again...")
        return -1, -1
    return desc, price


def notify(heading, text):
    """Ubuntu Notification in case of Price drop"""
    try:
        s.call(['notify-send', heading, "Decrease in price: " + str(text)])
    except Exception as error:
        print(error)
        print_red_bright("NotificationError")


def compare(curr_price, prev_price, desc):
    """Compare the current price with the price on file"""
    return_price = 0
    has_decreased_flag = 0
    if prev_price != sys.maxsize:
        if curr_price < int(float(prev_price)):
            print_green_bright("There is a decrease in price")
            print("Previous Lowest Price till now : " + str(int(float(prev_price))))
            notify(desc, curr_price)
            return_price = curr_price
            has_decreased_flag = 1
        elif curr_price > int(float(prev_price)):
            print_red_bright("There is an increase in price")
            print("Lowest Price till now : " + str(int(float(prev_price))))
            return_price = prev_price
            has_decreased_flag = 0
        else:
            print("This is same as the lowest price")
            return_price = curr_price
            has_decreased_flag = 0
    else:
        print_blue_bright("New product... You'll be notified of any price drop")
        return_price = curr_price
        has_decreased_flag = 2
    return return_price, has_decreased_flag


def write_to_file(filename, urls, commented_lines):
    """Write the new price, if lower to the same input file"""
    try:
        msg = ""
        for url in urls.keys():
            msg += "\n" + url.strip() + "|" + str(urls[url])
        with open(os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), filename),
                  'w') as u_f:
            u_f.write(msg[1:])
        if commented_lines:
            with open(os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])), filename),
                      'a') as u_f:
                u_f.write('\n' + ''.join(commented_lines))
    except Exception as error:
        print(error)
        system_exit_error("WriteToFileError")


def get_mail_credentails(filename):
    """Extract Credentials for EMAIL"""
    try:
        with open(filename, 'r') as m_f:
            data = json.load(m_f)

        return data
    except Exception as error:
        print(error)
        system_exit_error("MailCredentailsError")

def create_html(item, prev_price, curr_price, url):
    """Create HTML element for mail"""
    try:
        str_table = "<html><head><style>table, th, td {border: 1px solid black;}</style></head>"
        str_table += "<table style='width:100%'>"
        str_table += "<tr><td>ITEM</td><td>" + item + "</td></tr>"
        str_table += "<tr><td>URL</td><td>" + url + "</td></tr>"
        str_table += "<tr><td>Previous Price</td><td>" + str(prev_price) + "</td></tr>"
        str_table += "<tr><td>Current Price</td><td><b>" + str(curr_price) + "</b></td></tr>"
        str_table += "</table></html>"
        return str_table
    except Exception as error:
        print(error)
        system_exit_error("CreateHTMLError")


def send_mail(mail_creds_file, item, prev_price, curr_price, url):
    """Send a mail with the item details on price drop"""
    mail_credentails = get_mail_credentails(mail_creds_file)

    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_FROM
        msg['To'] = ', '.join(SUCCESS_MAIL_TO)
        msg['Subject'] = "Price drop for " + item

        text_body = "There is a price drop of Rs " + str(float(prev_price) - curr_price) +\
                    " that you might be interested in:\n\n"
        html_body = create_html(item, prev_price, curr_price, url)

        msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        server = smtplib.SMTP(mail_credentails['SMTP_SERVER'], mail_credentails['SMTP_PORT'])
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(mail_credentails['LOGIN_USER'], mail_credentails['LOGIN_PASSWORD'])
        server.sendmail(MAIL_FROM, SUCCESS_MAIL_TO, msg.as_string())
    except Exception as error:
        print(error)
        system_exit_error("PriceEmailError")


def get_price(url_file_name, proxies, mail_creds_file):
    """First function to be called.
    It calls all other functions when being called from the main function"""
    urls, commented_lines = get_urls(url_file_name)
    print("Total Proxies : {}".format(len(proxies)))

    sum_changed_price = 0
    has_failed_to_get_html = 0

    for url in urls:
        print_new_line()
        html = get_html(url, proxies)

        if html != -1:
            desc, price = extract(url, html)

            if (desc, price) != (-1, -1):
                print(desc)
                print("({})".format(url.strip("\n")))
                print("Current Price: {}".format(price))

                prev_price_to_compare = urls[url]
                current_price, to_send_mail_flag = compare(price, prev_price_to_compare, desc)

                if to_send_mail_flag == 1:
                    send_mail(mail_creds_file, desc, prev_price_to_compare, current_price, url)

                sum_changed_price += to_send_mail_flag

                urls[url] = str(current_price).strip()
            else:
                has_failed_to_get_html += 1
        else:
            has_failed_to_get_html += 1
            print_red_bright("Could not fetch page with URL:\n{}".format(url))

    if sum_changed_price > 0:
        write_to_file(url_file_name, urls, commented_lines)

    return has_failed_to_get_html


def send_failure_alert_mail(mail_creds_file):
    """Send a mail if there are failures"""
    mail_credentails = get_mail_credentails(mail_creds_file)

    try:
        msg = MIMEMultipart()
        msg['From'] = MAIL_FROM
        msg['To'] = ', '.join(FAILURE_MAIL_TO)
        msg['Subject'] = "NNTO : Amazon Price Watcher failures"

        text_body = ""
        msg.attach(MIMEText(text_body, 'plain'))

        server = smtplib.SMTP(mail_credentails['SMTP_SERVER'], mail_credentails['SMTP_PORT'])
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(mail_credentails['LOGIN_USER'], mail_credentails['LOGIN_PASSWORD'])
        server.sendmail(MAIL_FROM, FAILURE_MAIL_TO, msg.as_string())
    except Exception as error:
        print(error)
        system_exit_error("SendReportError")


def check_failures(log_file_name, number_lines, mail_creds_file):
    """Send a email if last number_lines runs are Failure"""
    try:
        last_n_status = os.popen("tail -{} {}".format(number_lines, log_file_name)).read()
        last_n_status = last_n_status.split("\n")[:number_lines]
        last_n_status = list({i.split(": ")[1] for i in last_n_status})

        if "SUCCESSFUL" not in last_n_status:
            send_failure_alert_mail(mail_creds_file)
    except Exception as error:
        print(error)
        system_exit_error("CheckFailureError")


def system_exit_error(msg):
    """Write Error log and exit"""
    stop_time = strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE_NAME, 'a') as l_f:
        l_f.write(START_TIME + " " + stop_time + ": " + msg)
        l_f.write("\n")
    check_failures(LOG_FILE_NAME, CHECK_LAST_N_LINES, MAIL_CREDENTIALS_FILE)
    sys.exit(0)


def system_exit_success():
    """Write SUCCESFUL Run log and Exit"""
    stop_time = strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE_NAME, 'a') as l_f:
        l_f.write(START_TIME + " " + stop_time + ": SUCCESSFUL")
        l_f.write("\n")
    sys.exit(0)


if __name__ == '__main__':
    try:
        FILE_NAME, LOG_FILE_NAME, MAIL_CREDENTIALS_FILE,\
        CHECK_LAST_N_LINES = get_config("config.json")
        clear_screen()
        PROXIES = get_proxies()
        STATUS = get_price(FILE_NAME, PROXIES, MAIL_CREDENTIALS_FILE)

        if STATUS:
            system_exit_error("GetPriceError")
        else:
            system_exit_success()
    except Exception as main_error:
        print(main_error)
        system_exit_error("Errors")
