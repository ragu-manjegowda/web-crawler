## Web Crawler for nammaMysuru Android App. 

##Import for calling spark cluster python script 
import sys
import subprocess 
from subprocess import PIPE 

##Import Beautiful Soup, URL LIBRARY and Wikipedia
from bs4 import BeautifulSoup
import urllib
import urllib2
import wikipedia
import re

##SQLITE3 set up 
import sqlite3
conn = sqlite3.connect('nammaMysuru.sqlite')
cur = conn.cursor()

##set Wiki language to English
wikipedia.set_lang('en')

##URL to crawl - http://www.masthmysore.com/movies-in-mysore
r = urllib.urlopen('http://www.masthmysore.com/movies-in-mysore').read()
soup = BeautifulSoup(r, "html.parser")

##Movie Data is in Table
table = soup.find('table', {'class': 'table'})

##An empty List to store crawled data 
ListCrawled=[] 

##An empty List to return JSON type data 
MovieList = [] 
TheaterList = [] 
DRCList = [] 
INOXList = [] 

##To check if it is just a language category and not data  
checkCategory = False 

##To store movie Language 
movieLanguage = ' '

##tr has content tr[0] in first iteration, tr[1] in second and so on. Refer - https://docs.python.org/2.3/whatsnew/section-enumerate.html  
for j,tr in enumerate(table.findAll("tr")):
	
	## tr[0] has non Movie Data (some styling structure)
	#if j == 0:
		#continue
	##td has content td[0] in first iteration, td[1] in second and so on. Refer - https://docs.python.org/2.3/whatsnew/section-enumerate.html 
	for i, td in enumerate(tr.findAll('td')):
		##data has text having all information for each movie (Movie name, Theater name and Timings)
		dataCrawled = td.text.strip() 
		dataCrawled = dataCrawled.encode('ascii','ignore')
		
		##Logic to check category and skipping parsing the next iteration too 
		length = len(tr.find_all('td')) 
		if i == 0 and length == 1: 
		#if i == 0 and str(td.img) == 'None':
			#movieLang = str(dataCrawled)
			movieLang2 = str(td.img['src']).split('/')
			movieLanguage =  movieLang2[-1].split(' ')[0]
			#match = re.search('(\w+)', movieLang)
			#if match: 
				#movieLanguage = match.group(1)
			checkCategory = True 
			continue 
		elif checkCategory: 
			checkCategory = False
			#continue 
		
		##data in td[0] has Movie Name 
		if i == 0: 
			dicCrawled = {}
			list_multiplex_times =[]
			list_multiplex_names =[]
			dicCrawled['theaters'] = []
			#dicCrawled['movieLanguage'] = 'Kannada'
			dicCrawled['movieLanguage'] = movieLanguage
			dicCrawled['multiplex'] = []
			dicCrawled['Movie']=dataCrawled
			dicCrawled['image']=str(td.img['src'])
		else:
			##Variable to count number of multiplex 
			multiplexCount = 0
			
			##Split data by new line
			linesCrawled = dataCrawled.split('\n') 
			
			##remove blank lines if any 
			linesCrawled  = [line for line in linesCrawled if line.strip()]
			
			##check all paragraphs (in source HTML Multiplex are in seperate 'p' and all theaters in one 'p')
			for k, p in enumerate(td.findAll('p')): 
				
				##if there is img attribute then it is multiplex 
				if str(p.img) != 'None': 
					
					##count number of multiplex 
					multiplexCount = multiplexCount + 1
					
					##store multiplex name 
					list_multiplex_names.append(p.img['alt']) 
					
			##append show times to list 
			for l, time in enumerate(linesCrawled):
				if l <  multiplexCount: 
					list_multiplex_times.append(time)
				else: 
					dicCrawled['theaters'].append(time)
					dicCrawled['multiplex'].append(str(0))
		
		##Append multiplex data to end of list 
		for name_ ,time_ in zip(list_multiplex_names,list_multiplex_times):
			dicCrawled['theaters'].append(str("%s : %s"%(name_.strip(), time_.strip())))
			dicCrawled['multiplex'].append(str(1))
		
		#add movie data only once in dictionary. if we remove if it will add twice because there are two colums in the table
		if i==0:
			ListCrawled.append(dicCrawled.copy())	

#print ListCrawled 
#sys.exit() 

##Store Multiplex details before parsing movie data as we won't show movie details of Multiplex in theater data 
##Iterate only once, doing this to avoid making dictionary global  
for i in range(0, 1):
	dicTheater = {}
	dicTheater['Multiplex'] =  '1'
	dicTheater['Multiplex_ClassName'] = 'DRC' 
	dicTheater['movie_Name'] = ' ' 
	dicTheater['show_timings'] = ' ' 
	dicTheater['theaterName'] = 'DRC' 
	TheaterList.append(dicTheater.copy())
	dicTheater = {}
	dicTheater['Multiplex'] =  '1'
	dicTheater['Multiplex_ClassName'] = 'INOX' 
	dicTheater['movie_Name'] = ' '   
	dicTheater['show_timings'] = ' ' 
	dicTheater['theaterName'] = 'INOX' 
	TheaterList.append(dicTheater.copy()) 

##List to store Movie Names for YouTube search using Spark 
movieQueryList = []
 	
##Parse Crawled List and format data to store in database 
for x in ListCrawled:
	
	##Placeholder for list of theaters and show times 
	theaterListCrawled = x['theaters'] 

	##Placeholder for list of multiplex check 
	multiplexCheckCrawled = x['multiplex'] 

	##Take movie name and remove certificate inside braces 
	movieName = x['Movie']
	indexCertificate = movieName.find('(') 
	if indexCertificate != -1: 
		movieName = movieName[:movieName.find('(')] 
	
	##Placeholders for Movies JSON to store in database 
	
	
	##Movies has - movie_Image, movie_Info, movie_Name, movie_Trailer,  
	dicMovies = {} 
	
	##Store movie name in dictionary 
	dicMovies['movie_Name'] = movieName
	
	##Store movie language in dictionary 
	dicMovies['movie_Language'] = x['movieLanguage']
	
	##Store URL to movie image in dictionary 
	dicMovies['movie_Image'] = x['image'] 
	
	##Search text for movie 
	movieSearchText = dicMovies['movie_Name'] + ' ' + dicMovies['movie_Language'] + ' movie' 
	
	##Search Wiki for movie page 
	#print movieSearchText
	results = wikipedia.search(movieSearchText, results=5, suggestion=False)
	#print results

	##Get article for first search result 
	try: 
		##store url of article in dictionary 
		article = wikipedia.page(title=results[0], pageid=None, auto_suggest=False, redirect=True, preload=False)
		dicMovies['movie_Info'] = str(article.url)
	except: 
		##redirect to default page if there is exception
		dicMovies['movie_Info'] = 'https://en.wikipedia.org/w/index.php?search=' + str(movieSearchText)

	##Search YouTube for Trailer 
	textToSearch = movieSearchText  +  ' official trailer'

	##Append trailer Query text to List 
	movieQueryList.append(textToSearch)

	##Store each movie in List 
	MovieList.append(dicMovies)

	##Process theater details 
	for theaters_, multiplexCheck_ in zip(theaterListCrawled, multiplexCheckCrawled):
		
		line = theaters_.split(',')
		dataFirst =  line[0] 
		theaterName = str(dataFirst)
		try: 
			index = theaterName.index(':')
		except: 
			index = len(theaterName) 
		theaterName = theaterName[:index].strip()

		line[0] = dataFirst[dataFirst.find(':')+1:].strip()
		line = ''.join(line) 
		
		##Check if it is Multiplex 
		if multiplexCheck_ == str(1): 
			##If DRC append to DRC list 
			if theaterName.lower() == 'drc': 
				dicDRC = {} 
				dicDRC['movie_Name'] = movieName
				dicDRC['show_timings'] = line 
				dicDRC['theaterName'] = 'DRC'
				DRCList.append(dicDRC.copy()) 
			##If INOX append to INOX list 
			elif theaterName.lower() == 'inox': 
				dicINOX = {} 
				dicINOX['movie_Name'] = movieName 
				dicINOX['show_timings'] = line 
				dicINOX['theaterName'] = 'INOX' 
				INOXList.append(dicINOX.copy())
		else: 
			#Thearer has - Multiplex, Multiplex_ClassName, movie_Name, show_timings, theater_Address, theater_Image, theater_Location, theater_Name, theater_Phone_ 
			dicTheater = {}
			dicTheater['Multiplex'] = '0' 
			dicTheater['Multiplex_ClassName'] = ' '
			
			dicTheater['show_timings'] = line
			dicTheater['movie_Name'] = movieName
			dicTheater['theaterName'] = theaterName 
			TheaterList.append(dicTheater.copy()) 

#print DRCList
#print 'DRC' + '-----------------------------------' 
#print INOXList 
#print 'INOX' + '----------------------------------'
#print TheaterList
#print MovieList
#sys.exit()

#print movieQueryList

#Define movie trailer get function
def getYouTubeString(searchText):
        query = urllib.quote(searchText)
        url = "https://www.youtube.com/results?search_query=" + query
        response = urllib2.urlopen(url)
        html = response.read()
        soup = BeautifulSoup(html)
        vid = soup.findAll(attrs={'class':'yt-uix-tile-link'})
        ##Out of all results get url for first result 
        dataFirst = vid[1]['href']
        movieVideo = str(dataFirst[dataFirst.find('=')+1:])
        ##Store Video ID in dictionary 
        return movieVideo

movieQueryResultList = []
for movie in movieQueryList:
	queryResult = getYouTubeString(movie)
	movieQueryResultList.append(queryResult)

##Spark Cluster setup for trailer query 
#cmd = subprocess.Popen(["python","spark.py"]+movieQueryList, stdout=subprocess.PIPE)
#output = cmd.communicate()[0] 
#print output

##Output has extra details, trailer details are in first field before newline 
#output = output.split('\n')
#movieQueryResultList = output[0].replace('[', "")
#movieQueryResultList = movieQueryResultList.replace(']', "")
#movieQueryResultList = movieQueryResultList.replace("'", "") 
#movieQueryResultList = movieQueryResultList.split(',')
#movieQueryResultList = []

##Trailer details has some junk data at 0 (zero)th index so delete it 
#del movieQueryResultList[0]

#print movieQueryResultList
#sys.exit()

##Store all three list into SQLite3 Database 
cur.executescript(''' 
DROP TABLE IF EXISTS movies; 
DROP TABLE IF EXISTS theater; 
DROP TABLE IF EXISTS drc; 
DROP TABLE IF EXISTS inox;  

CREATE TABLE movies (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	movie_Trailer TEXT,
	movie_Image TEXT,
	movie_Language TEXT, 
	movie_Name TEXT, 
	movie_Info TEXT 
); 

CREATE TABLE theater (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	Multiplex_ClassName TEXT, 
	movie_Name TEXT, 
	Multiplex TEXT, 
	show_timings TEXT, 
	theaterName TEXT, 
	theaterID TEXT
); 

CREATE TABLE drc (
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
	show_timings TEXT, 
	movie_Name TEXT, 
	theaterName TEXT 
);    

CREATE TABLE inox ( 
	id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE, 
	show_timings TEXT,
	movie_Name TEXT,
	theaterName TEXT
)
''') 

##Start Inserting Movie Data 
for x, y in zip(MovieList, movieQueryResultList): 
	#trailer string has spaces and string symbols, remove then before insert 
	y = y.replace(" ","") 
	movie_Trailer = y
	#movie_Trailer = "c4VF_m8zvo4"
	movie_Image = x['movie_Image'] 
	movie_Language = x['movie_Language'] 
	movie_Name = x['movie_Name'] 
	movie_Info = x['movie_Info'] 

	cur.execute('''INSERT OR IGNORE INTO movies (movie_Trailer, movie_Image, movie_Language, movie_Name, movie_Info) VALUES ( ?, ?, ?, ?, ? )''', (movie_Trailer, movie_Image, movie_Language, movie_Name, movie_Info ) )	

for x in TheaterList:
	Multiplex_ClassName = str(x['Multiplex_ClassName'])
	movie_Name = str(x['movie_Name'])
	Multiplex = str(x['Multiplex'])
	show_timings = str(x['show_timings'])
	theaterName = str(x['theaterName'])
	
	print(theaterName)
	print(movie_Name)

	if theaterName == '4':
		continue

        if theaterName == '10':
                continue
        if theaterName == '30 AM':
                continue

	if theaterName == '9':
		continue

	if theaterName == '(2D)Rajkamal':
		theaterName = 'Rajkamal'

	cur.execute('SELECT id FROM theaterDetail WHERE theaterName = ? ', (theaterName, ))
	
	theater_id = cur.fetchone()[0] 

	cur.execute('''INSERT OR IGNORE INTO theater (Multiplex_ClassName, movie_Name, Multiplex, show_timings, theaterName, theaterID) VALUES ( ?, ?, ?, ?, ?, ? )''', (Multiplex_ClassName, movie_Name, Multiplex, show_timings, theaterName, theater_id) )

for x in DRCList:
	show_timings = str(x['show_timings'])
	movie_Name = str(x['movie_Name'])
	theaterName = str(x['theaterName'])
        
	cur.execute('''INSERT OR IGNORE INTO drc (show_timings, movie_Name, theaterName) VALUES ( ?, ?, ? )''', (show_timings, movie_Name, theaterName) )

for x in INOXList:
	show_timings = str(x['show_timings'])
	movie_Name = str(x['movie_Name'])
	theaterName = str(x['theaterName'])

	cur.execute('''INSERT OR IGNORE INTO inox (show_timings, movie_Name, theaterName) VALUES ( ?, ?, ? )''', (show_timings, movie_Name, theaterName) ) 

conn.commit() 
