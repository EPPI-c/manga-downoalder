from .Site import Site
import requests, re, os, json
from bs4 import BeautifulSoup

class Mangayabu(Site):#add exceptions, last chapter, broken

    def __init__(self, link) -> None:
        super().__init__(link)

    headers = {
        'Referer': 'https://mangayabu.top/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.77 Safari/537.36',
    }

    def get_chapters(self, last_chapter=None):
        r = requests.get(self.link)
        soup = BeautifulSoup(r.content, "lxml")
        soup = soup.find("script", id="manga-info")
        chapters_json = json.loads(soup.text)
        chapters = []
        for chapter_json in chapters_json['allposts']:
            chapter_link = chapter_json['id']
            try:
                number = re.search(r'\d+(-\d+)*(?=[a-zA-Z]*-my)', chapter_link).group().removeprefix('capitulo-')
            except:
                continue
            if number == last_chapter:
                break
            chapters.append({'chapter_name': f"{chapters_json['chapter_name']}-{number}", 'href': chapter_json['id'], 'number':number})        
        
        return chapters
    
    def download_chapters(self, chapters, path=os.getcwd(), threads=3):# save last chapter
        def download(args):
            def downloadimg(image, path):
                r = requests.get(image, stream=True)
                with open(path, 'wb') as f:
                    for chunk in r:
                        f.write(chunk)           
            links = []
            for chapter in args[0]:
                path = os.path.join(args[1], self._clean_file_name(chapter['chapter_name']))
                if not os.path.exists(path):
                    os.mkdir(path)
                else:
                    counter = 0
                    cpath = path
                    while os.path.exists(path):
                        counter += 1
                        path = cpath + f'({counter})'
                    os.mkdir(path)
                r = requests.get(chapter['href'])
                soup = BeautifulSoup(r.content, 'html5lib')
                soup = soup.find('div', class_='section table-of-contents')
                soup = soup.find_all('img', class_='lazy scrollspy')
                for link in soup:
                    links.append(link['data-src'])
                for image in links:
                    counter += 1
                    imgname = os.path.join(path, f'{counter}.jpg')
                    downloadimg(image, imgname)

                    while not self._verifyimg(imgname):
                        downloadimg(image, imgname)

        self._run(path, chapters, threads, download)

    

