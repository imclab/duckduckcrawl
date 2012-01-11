#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, logging, time, urllib.parse, xml.etree.ElementTree
import httplib2
import ddc_process


class DistributedCrawlerClient():

  PROTOCOL_VERSION = 1
  http_client = httplib2.Http(timeout=10)

  def __init__(self,server,port):
    self.base_url = "http://%s:%d/rest" % (server,port)
  
  def start(self,):
    while True:
      # see README.md for params description
      response = self.request({ "action"          : "getdomains",
                                "version"         : str(self.PROTOCOL_VERSION),
                                "pc_version"      : str(ddc_process.VERSION) }).decode("utf-8")

      # read response
      xml_response = xml.etree.ElementTree.fromstring(response)
      xml_domains = xml_response.findall("domainlist/domain") # TODO use iterator
      domain_count = len(xml_domains)

      # TODO look for an upgrade node and act accordingly

      # if the server has no work for us, take a nap
      if not domain_count:
        logging.getLogger().info("Got no domains to check from server, sleeping for 30s...")
        time.sleep(30)
        continue

      # check domains
      logging.getLogger().info("Got %d domains to check from server" % (domain_count) )
      domains_state = [ False for i in range(domain_count) ]
      for (i, xml_domain) in enumerate(xml_domains):
        domain = xml_domain.get("name")
        logging.getLogger().debug("Checking domain '%s'" % (domain) )
        domains_state[i] = ddc_process.is_spam(domain)
        # TODO should add a special XML attribute for when a domain check fails (network, etc.)

      # prepare POST request content
      xml_root = xml.etree.ElementTree.Element("ddc")
      xml_domain_list = xml_response.find("domainlist") # reuse the previous XML domain list
      for (xml_domain, is_spam) in zip(xml_domain_list.iterfind("domain"),domains_state):
        xml_domain.set("spam",str(int(is_spam)))
      xml_root.append(xml_domain_list)

      # send POST request
      post_data = xml.etree.ElementTree.tostring(xml_root)
      self.request({ "action"     : "senddomainsdata",
                     "version"    : str(self.PROTOCOL_VERSION),
                     "pc_version" : str(ddc_process.VERSION) },
                   True,
                   post_data) # we don't care for what the server actually returns here

  def request(self,url_params,post_request=False,post_data=None):
    # construct url
    url = "%s?%s" % (self.base_url,urllib.parse.urlencode(url_params))
    # send request
    if post_request:
      logging.getLogger().info("Posting data to '%s'" % (url) )
      response, content = self.http_client.request(url,"POST",post_data)
    else:
      logging.getLogger().info("Fetching '%s'" % (url) )
      response, content = self.http_client.request(url)
    return content


if __name__ == '__main__':

  # setup logger
  logger = logging.getLogger()
  logger.setLevel(logging.DEBUG)

  # parse args
  cli_parser = argparse.ArgumentParser()
  cli_parser.add_argument("-s", 
                          "--server",
                          action="store",
                          required=True,
                          dest="server",
                          help="Server IP or domain to connect to")
  cli_parser.add_argument("-p", 
                          "--port",
                          action="store",
                          required=True,
                          type=int,
                          dest="port",
                          help="Network port to use to communicate with server")
  options = cli_parser.parse_args()
  
  # start client
  client = DistributedCrawlerClient(options.server,options.port)
  client.start()