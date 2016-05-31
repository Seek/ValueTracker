
# coding: utf-8

# In[2]:

import json, requests

url = 'https://tempostorm.com/api/decks/findOne?filter='

params = dict(
    where = dict(
        slug = "midrange-shaman-standard-meta-snapshot-may-29-2016",
        fields = {},
        include = []
    )
)


# In[3]:

params


# In[33]:

request = json.loads("""{"where":{"slug":"midrange-shaman-standard-meta-snapshot-may-29-2016"},"fields":["id","createdDate","name","description","playerClass","premium","dust","heroName","authorId","deckType","isPublic","chapters","youtubeId","gameModeType","isActive","isCommentable"],"include":[{"relation":"cards","scope":{"include":"card","scope":{"fields":["id","name","cardType","cost","dust","photoNames"]}}},{"relation":"comments","scope":{"fields":["id","votes","authorId","createdDate","text"],"include":{"relation":"author","scope":{"fields":["id","username","gravatarUrl"]}}}},{"relation":"author","scope":{"fields":["id","username"]}},{"relation":"matchups","scope":{"fields":["forChance","deckName","className"]}},{"relation":"votes","fields":["id","direction","authorId"]}]}""")


# In[34]:

request


# In[35]:

request['fields'] = {}


# In[39]:

request['include']


# In[38]:

request['include'] = [request['include'][0],]


# In[40]:

del request['include'][0]['scope']['scope']


# In[41]:

request


# In[44]:

json.dumps(request)


# In[46]:

resp = requests.get(url=url+json.dumps(request))
data = json.loads(resp.text)


# In[52]:

data['cards']


# In[ ]:



