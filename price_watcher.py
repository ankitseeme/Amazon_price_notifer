import os
import sys
import requests
from lxml.html import fromstring
from bs4 import BeautifulSoup
from random import shuffle
import subprocess as s
from colorama import Fore, Back, Style
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


login_user = "donotreply@ankit"
login_password = "a2I5cTNqeGhuZGkw"
smtp_server = "mail.smtp2go.com"
smtp_port = "2525"
from_addr = "ankitseeme@gmail.com"
to_addr = "ankitseeme@gmail.com"


class AccessError(Exception):
    pass


class NoPriceError(Exception):
    pass


def get_proxies():
    url = 'https://free-proxy-list.net/'
    response = requests.get(url)
    parser = fromstring(response.text)
    proxies = set()
    for i in parser.xpath('//tbody/tr')[:10]:
        if i.xpath('.//td[7][contains(text(),"yes")]'):
            #Grabbing IP and corresponding PORT
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
            proxies.add(proxy)
    return proxies


def get_urls(file_name):
    urls = {}
    try:
        with open(os.path.join(os.path.dirname(os.path.realpath(sys.argv[0])),file_name),'r') as f:
            for line in f:
                if line.find('www.amazon.in') != -1:
                    if len(line.split('|')) == 2:
                        urls[line.split('|')[0]] = line.split('|')[1]
                    else:
                        urls[line.split('|')[0]] = sys.maxsize
    except:
        print("Encountered some issue with input file... Please check")
        exit(1)
    print("Total Watched products = " + str(len(urls)))
    return urls


def get_html(url,proxies):
    proxies = list(proxies)
    shuffle(proxies)
    for proxy in proxies:
        try:
            html = requests.get(url,proxies={"http":proxy,"https":proxy},timeout=20)
        except:
            pass
        else:
            if html.status_code == 200:
                return html
    try:
        html = requests.get(url)
        if html.status_code == 200:
            return html
    except:
        print("Unable to access the page with URl : {} ".format(url))
        print("Please check the URL, and if you think it is correct, please try again")
    return -1



def extract(html):
    bsobj = BeautifulSoup(html.text,'lxml')
    try:
        desc = bsobj.find('span',{'id':'productTitle'}).text.strip()
    except:
        print("We ran into some trouble... Please try again")
        return -1,-1
    try:
        if bsobj.find('span',{'id':'priceblock_dealprice'}):
            price = int(float(bsobj.find('span',{'id':'priceblock_dealprice'}).text.replace(',','').strip()))
        elif bsobj.find('span',{'id':'priceblock_ourprice'}):
            price = int(float(bsobj.find('span',{'id':'priceblock_ourprice'}).text.replace(',','').strip()))
        else:
            raise NoPriceError
    except NoPriceError:
        print("Can't find price... Please try again...")
        return -1,-1
    return desc,price


def notify(heading,text):
    try:
        s.call(['notify-send',heading,"Decrease in price: " + str(text)])
    except:
        print("NotificationError")



def compare(curr_price,prev_price,desc):
    if prev_price != sys.maxsize:
        if curr_price < int(float(prev_price)):
               print("There is a decrease in price")
               notify(desc,curr_price)
               return curr_price,1
        elif curr_price > int(float(prev_price)):
            print("There is an increase in price")
            print("Lowest Price till now : " + str(int(float(prev_price))))
            return prev_price,0
        else:
            print("This is same as the lowest price")
            return curr_price,0
    else:
        print("New product... You'll be notified of any price drop")
        return curr_price,0


def write_to_file(filename,urls):
    msg=""
    for url in urls.keys():
        msg += "\n" + url.strip() + "|" + str(urls[url])
    with open(filename,'w') as f:
            f.write(msg[1:])


def send_mail(item, prev_price, curr_price, url):
    msg = MIMEMultipart()
    msg['From'] = login_user
    msg['To'] = to_addr
    msg['Subject'] = "Price drop for " + item
    body = "Previous Price".ljust(20) + str(prev_price)
    body += "\n" + "Current Price".ljust(17) + str(curr_price)
    body += "\n" 
    body += "\n" + "Item URL".ljust(17) + str(url)
    body += "\n\n\n" + "End of message"
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP(smtp_server, smtp_port)
    server.ehlo()
    server.starttls()
    server.ehlo()
    server.login(login_user, login_password)
    text = msg.as_string()
    server.sendmail(from_addr, to_addr, text)


def get_price(file_name):
    proxies = get_proxies()
    os.system('clear')
    urls = get_urls(file_name)
    print("Total Proxies : {}".format(len(proxies)))
    for url in urls.keys():
        print("\n")
        html = get_html(url,proxies)
        if html != -1:
            desc, price = extract(html)
            if (desc,price) != (-1,-1):
                print(desc)
                print("({})".format(url))
                print("Current Price: {}".format(price))
                price_to_write, to_send_mail_flag = compare(price,urls[url],desc)
                if to_send_mail_flag == 1:
                    send_mail(desc,urls[url],price_to_write,url)
                urls[url] = str(price_to_write).strip()
        else:
        	print("Could not fetch page with URL: {}".format(url))
    write_to_file(file_name,urls)
    #exit_status = input("Press Enter to Exit\n")


if __name__ == '__main__':
    file_name = 'amazon_urls.txt'
    get_price(file_name)



