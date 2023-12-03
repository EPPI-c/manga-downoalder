import asyncio
import json
import os
import re
from bs4 import BeautifulSoup
from .Site import Site


class Mangasee(Site):#last chapter exceptions

    def __init__(self, link, name, workers) -> None:
        super().__init__(link, name, workers)

    headers = {
        'authority': 'mangasee123.com',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'sec-gpc': '1',
        'sec-fetch-site': 'none',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-user': '?1',
        'sec-fetch-dest': 'document',
        'accept-language': 'en-US,en;q=0.9',
    }
    async def get_chapters(self, last_chapter):
        '''gets a list of chapters until last_chapter, if last_chapter is None gets all chapters'''
        chapters = []
        name = self.link.replace('https://mangasee123.com/manga/', '')
        link = f"https://mangasee123.com/rss/{name}.xml"
        content = await self.fetch_text(link)
        if not content: return
        soup = BeautifulSoup(content, 'html5lib')
        items = soup.find_all('item')
        for item in items:
            title = item.find('title')
            number = float(re.search(r' [+-]?([0-9]+([.][0-9]*)?|[.][0-9]+)', title.text).group(0).removeprefix(' '))
            title = f'{self.name}-{number}'
            if number == float(last_chapter):
                break
            chapters.append({'chapter_name': title, 'href': re.search(r'https:.*\.html', item.text).group(0), 'number':number})

        return chapters

    async def download_chapters(self, chapters, path):
        '''chapters = list with json files of chapter objects
        path = path where the chapters are going to be safed'''
        for chapter in chapters:
            path = os.path.join(path, self._clean_file_name(chapter['chapter_name']))
            if not os.path.exists(path):
                os.mkdir(path)
            else:
                counter = 0
                cpath = path
                while os.path.exists(path):
                    counter += 1
                    path = cpath + f'({counter})'
                os.mkdir(path)
            content = await self.fetch_text(chapter['href'])
            if not content: return
            soup = BeautifulSoup(content, 'html5lib')
            footer = re.search(r' MainFunction.* MainFunction', str(soup), re.DOTALL).group()
            # get href
            href = soup.find('div', attrs={'ng-if': "!vm.Edd.Active"}).find('img')['ng-src']

            # get vm.CurPathName
            CurPathName = re.search(r'vm.CurPathName = ".*"', footer).group().removeprefix('vm.CurPathName = "').removesuffix('"')

            # get vm.CurChapter
            CurChapter = re.search(r'vm.CurChapter = {.*;', footer).group().removeprefix('vm.CurChapter = ').removesuffix(';')
            CurChapter = json.loads(CurChapter)

            if CurChapter['Directory'] != "":
                Directory = CurChapter['Directory'] + '/'
            else:
                Directory = CurChapter['Directory']

            chapterimage = self.__chapter_image(CurChapter['Chapter'])

            links = self.__get_links(href, CurPathName, Directory, chapterimage, CurChapter)

            images = [asyncio.ensure_future(self.fetch_image(image, os.path.join(path, f'{i}.jpg')))
                      for i, image in enumerate(links,1)]
            await asyncio.gather(*images)

    def __chapter_image(self, chapterstring):
        chapter = chapterstring[1:-1]
        if chapterstring[-1] != '0':
            chapter = chapter + '.' + chapterstring[-1]
        return chapter

    def __get_links(self, href, CurPathName, Directory, chapterimage, CurChapter):
        links = []

        def PageImage(page):
            s = '000' + page
            return s[-3:]

        def get_link(href, CurPathName, Directory, chapterimage, page):
            link = href.replace('{{vm.CurPathName}}', CurPathName)
            link = link.replace("{{vm.CurChapter.Directory == '' ? '' : vm.CurChapter.Directory+'/'}}", Directory)
            link = link.replace('{{vm.ChapterImage(vm.CurChapter.Chapter)}}', chapterimage)
            link = link.replace('{{vm.PageImage(Page)}}', page)
            return link

        for page in range(1, int(CurChapter['Page'])+1):
            page = PageImage(str(page))
            links.append(get_link(href, CurPathName, Directory, chapterimage, page))

        return links
