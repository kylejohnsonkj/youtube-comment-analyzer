import re
import math
import urllib.request
import os
import subprocess
import json
import pandas as pd

API_KEY = '{YOUR API KEY HERE}'

print('YouTube Comment Analyzer')
print('------------------------')

def analyzeData():
	count = subprocess.check_output("jq '.items | length' data.json", shell=True)
	print('{} comments successfully processed'.format(int(count)))

	with open('data.json') as f:
		data = json.load(f)

		df = pd.json_normalize(data, 'items')

		# sort by date, likeCount, etc.
		df = df.sort_values(by=['snippet.topLevelComment.snippet.publishedAt'], ascending=False)
		
		# create url from videoId for quick access
		df['snippet.videoId'] = df['snippet.videoId'].map('https://youtu.be/{}'.format)
		df['snippet.videoId'] = df[['snippet.videoId', 'id']].agg('&lc='.join, axis=1)

		# limit values to include in csv
		df = df[['snippet.videoId', 'snippet.topLevelComment.snippet.publishedAt', 'snippet.topLevelComment.snippet.likeCount', 'snippet.topLevelComment.snippet.textOriginal']]

		df.to_csv('data.csv', encoding='utf-8', index=False)
		print('Analyzing Complete - See data.csv for results')

if os.path.exists('data.json'):
	analyzeData()
	quit()

#1 - parse my-comments.html for comment ids
path = 'Takeout/YouTube and YouTube Music/my-comments/'
commentIds = []

with open(path + 'my-comments.html') as f:
	html = f.read()
	# use regex to capture comment id in self-posted top level comments
	for match in re.finditer('You added a.*?&amp;lc=((?!\.).*?)\">comment', html):
		commentIds.append(match.group(1))

print('Found {} potential comments'.format(len(commentIds)))


#2 - fetch comment details in json format (max of 50 ids per request)
url = 'https://www.googleapis.com/youtube/v3/commentThreads?part=snippet&key={}'.format(API_KEY)
fetchUrl = url
fetchLimit = 50

fetchNum = 0
idForFetch = 0
numFetches = math.ceil(len(commentIds) / 50)

def fetchComments(fetchUrl, fetchNum, idForFetch):
	if not os.path.exists('data'):
		os.makedirs('data')
	print('... data/{}.json'.format(fetchNum))
	urllib.request.urlretrieve(fetchUrl, 'data/{}.json'.format(fetchNum))

	fetchNum += 1	
	fetchUrl = url
	idForFetch = 0
	return fetchUrl, fetchNum, idForFetch

print('Downloading comments')

for commentId in commentIds:
	fetchUrl += '&id={}'.format(commentId)
	idForFetch += 1
	if idForFetch == fetchLimit:
		fetchUrl, fetchNum, idForFetch = fetchComments(fetchUrl, fetchNum, idForFetch)

# if we have leftover ids (always unless % 50)
if idForFetch > 0:
	fetchUrl, fetchNum, idForFetch = fetchComments(fetchUrl, fetchNum, idForFetch)

# combine json into master data.json
# to get number of successful records: jq '.items | length' data.json
os.system("jq -s '.[0].items=([.[].items]|flatten)|.[0]' data/*.json > data.json")

analyzeData()
