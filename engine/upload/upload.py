# -*- coding: utf-8 -*-
# If on Python 2.X
from __future__ import print_function
import pysolr
import sys
import os
from zipfile import ZipFile
from os.path import join, splitext, exists
import xml.etree.ElementTree as ET

WORDS = ['W', 'QW']
LINE = ['L']
ZIP_PATH = "Document.zip"
FOLDER_PATH = "Document"
TOC_PATH = "TOC.xml"
PAGE = "Pg"
ARTICLE = "Ar"
AD = "Ad"

class Page(object):
    def __init__(self, file_stream):
        self.METADATA = METADATA= {
                                   "Entity" : self._parse_entity,}

        self.entities = {}
        self.articles = []

        tree = ET.parse(file_stream)
        root = tree.getroot()

        for element in root.getchildren():
            if element.tag in self.METADATA:
                self.METADATA[element.tag](element)

    def _parse_entity(self, element):
        box = None
        ID = None
        entity_name = None

        for child in element.getchildren():
            if child.tag == "Name":
                entity_name = child.text

        for name, item in element.items():
            if name == 'BOX':
                box = item
            if name == 'ID':
                id_ = item

        self.entities[id_] = {'box': box,
                              'headline': entity_name}

    def add_article(self, article):
        self.articles.append(article)

        if article.id in self.entities:
            attrs = self.entities[article.id].items()
            for attr_name, attr_value in attrs:
                article._info[attr_name] = attr_value

    def get_articles(self):
        return [ar._info for ar in self.articles]


class Article(object):
    def _parse_META(self, element):

        for name, item in element.items():
            if name == 'ISSUE_DATE':
                self._info['issue_date'] = item
            if name == 'PUBLICATION':
                self._info['publisher'] = item


    def _parse_Link(self, element):
        pass

    def _parse_Content(self, element):
        content = ''

        for primative in element.getchildren():
            for term in primative.getchildren():
                if term.tag in WORDS:
                    content += term.text
                #if term.tag in LINE:
                content += " "

        self._info['content'] = content


    def __init__(self, file_stream):
        self.METADATA = METADATA= {
                                   "Meta" : self._parse_META,
                                   "Link" : self._parse_Link,
                                   "Content": self._parse_Content }
        self._info = {}
        tree = ET.parse(file_stream)
        root = tree.getroot()
        doc_id = "" #TODO: Fixme should not be empty
        for name, item in root.items():
            if name == 'DOC_UID':
                doc_id = item
            if name == 'ID':
                id_ = item

        self.id = id_
        self._info['id'] = doc_id + id_

        for element in root.getchildren():
            if element.tag in self.METADATA:
                self.METADATA[element.tag](element)

def upload_dir_from_folder(solr,path):
    from os import walk, mkdir
    for root, dirs, files in walk(join(path, FOLDER_PATH)):
        page = ""
        articles = []
        ads = []
        for f in files:
            if f.endswith(".xml"):
                if PAGE in f:
                    page = f
                elif ARTICLE in f:
                    articles.append(f)
                elif AD in f:
                    ads.append(f)
        if page:
            page = Page(open(join(root,page), "r"))
            for article in articles:
                # Create the article object.
                ar = Article(open(join(root,article), "r"))
                # Add it to the page.
                page.add_article(ar)

            # Add the articles to solr.
            solr.add(page.get_articles())


def upload_dir_from_zip(solr,path):

    with ZipFile(join(path, ZIP_PATH)) as zip_file:
        # Find all the pages in the current zip.
        pages = [info for info in zip_file.infolist()
                     if (PAGE in info.filename and
                          info.filename.endswith(".xml"))]

        for page_file in pages:
            print(page_file.filename)
            # Create a page object.
            page = Page(zip_file.open(page_file.filename, "r"))

            page_dir = os.path.dirname(page_file.filename)

            # Find all the articles in the given page.
            article_files = [info for info in zip_file.infolist()
                                  if (page_dir+"/" in info.filename and
                                      ARTICLE in info.filename and
                                      info.filename.endswith(".xml"))]

            # Find all the articles in the given page.
            ad_files = [info for info in zip_file.infolist()
                                  if (page_dir+"/" in info.filename and
                                      AD in info.filename and
                                      info.filename.endswith(".xml"))]

            # TODO: also search the Ads

            for article_file in article_files:
                # Create the article object.
                ar = Article(zip_file.open(article_file.filename, "r"))
                # Add it to the page.
                page.add_article(ar)

            # Add the articles to solr.
            solr.add(page.get_articles())


def upload_all(solr, input_folder):
    from os import walk, mkdir

    for root, dirs, files in walk(input_folder):
        if TOC_PATH in files:
            if ZIP_PATH in files:
                upload_dir_from_zip(solr,root)
            elif FOLDER_PATH in dirs:
                upload_dir_from_folder(solr,root)

def main(argv):
    # Setup a Solr instance. The timeout is optional.
    solr = pysolr.Solr('http://localhost:8983/solr/', timeout=10)
    # You can optimize the index when it gets fragmented, for better speed.
    solr.optimize()
    
    upload_all(solr, argv[1])


if __name__ == "__main__":
    main(sys.argv)
