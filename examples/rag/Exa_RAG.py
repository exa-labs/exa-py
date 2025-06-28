#!/usr/bin/env python
# coding: utf-8

# # RAG: Answer your questions with context

# LLMs are powerful because they compress large amounts of data and patterns into a format that allows convenient access, but this compressions isn't lossless. Exa can bring the most relevant data into context. This lets us to combine the compressed data of the LLM with a select quantity of uncompressed data for the problem at hand for the best generations possible.

# Exa's SDKs make incorporating quality data into your LLM pipelines quick and painless. Install the SDK by running this command in your terminal:

# `pip install exa-py`

# In[1]:


# Now, import the Exa class and pass your API key to it.
from exa_py import Exa
import os

my_exa_api_key = os.environ.get("EXA_API_KEY")
if not my_exa_api_key:
    raise ValueError("EXA_API_KEY environment variable not set")
exa = Exa(my_exa_api_key)


# For our first example, we'll set up Exa to answer questions with OpenAI's popular GPT 3.5 model. (You can use GPT 4 or another model if you prefer!) We'll use Exa's `highlight` feature, which directly returns relevant text of customizable length for a query. You'll need to run `pip install openai` to get access to OpenAI's SDK if you haven't used it before. More information about the OpenAI python SDK can be found [here](https://platform.openai.com/docs/quickstart?context=python).

# In[2]:


# Set up OpenAI' SDK
from openai import OpenAI
import os

openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")
openai_client = OpenAI(api_key=openai_api_key)


# Now, we just need some questions to answer!

# In[3]:


questions = [
    "How did bats evolve their wings?",
    "How did Rome defend Italy from Hannibal?",
]


# While LLMs can answer some questions on their own, they have limitations:
# - LLMs don't have knowledge past when their training was stopped, so they can't know about recent events
# - If an LLM doesn't know the answer, it will often 'hallucinate' a correct-sounding response, and it can be difficult and inconvenient to distinguish these from correct answers
# - Because of the opaque manner of generation and the problems mentioned above, it is difficult to trust an LLM's responses when accuracy is [important](https://www.forbes.com/sites/mollybohannon/2023/06/08/lawyer-used-chatgpt-in-court-and-cited-fake-cases-a-judge-is-considering-sanctions/?sh=27194eb67c7f)
#
# Robust retrieval helps solve all of these issues by providing a quality sources of ground truth for the LLM (and their human users) to leverage. Let's use Exa to get some information about our questions:

# In[4]:


# Parameters for our Highlights search
highlights_options  = {
    "num_sentences": 7, # how long our highlights should be
    "highlights_per_url": 1, # just get the best highlight for each URL
}

# Let the magic happen!
info_for_llm = []
for question in questions:
    search_response = exa.search_and_contents(question, highlights=highlights_options, num_results=3, use_autoprompt=True)
    info = [sr.highlights[0] for sr in search_response.results]
    info_for_llm.append(info)


# In[5]:


info_for_llm


# Now, let's give the context we got to our LLM so it can answer our questions with solid sources backing them up!

# In[6]:


responses = []
for question, info in zip(questions, info_for_llm):
  system_prompt = "You are RAG researcher. Read the provided contexts and, if relevant, use them to answer the user's question."
  user_prompt = f"""Sources: {info}

  Question: {question}"""

  completion = openai_client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
      {"role": "system", "content": system_prompt},
      {"role": "user", "content": user_prompt},
    ]
  )
  response = f"""
  Question: {question}
  Answer: {completion.choices[0].message.content}
  """
  responses.append(response)


# In[7]:


from pprint import pprint # pretty print
pprint(responses)


# Exa can be used for more than simple question answering. One superpower of embeddings-based search is that we can search for the meaning for sentences or even paragraphs:

# In[8]:


paragraph = """Georgism, also known as Georgism, is an economic philosophy and ideology named after the American political economist Henry George (1839–1897). This doctrine advocates for the societal collective, rather than individual property owners, to capture the economic value derived from land and other natural resources. To this end, Georgism proposes a single tax on the unimproved value of land, known as a "land value tax," asserting that this would deter speculative land holding and promote efficient use of valuable resources. Adherents argue that because the supply of land is fundamentally inelastic, taxing it will not deter its availability or use, unlike other forms of taxation. Georgism differs from Marxism and capitalism, underscoring the distinction between common and private property while largely contending that individuals should own the fruits of their labor."""
query = f"The best academic source about {paragraph} is (paper: "
georgism_search_response = exa.search_and_contents(paragraph, highlights=highlights_options, num_results=5, use_autoprompt=False)


# In[9]:


for result in georgism_search_response.results:
    print(result.title)
    print(result.url)
    pprint(result.highlights)


# Using Exa, we can easily find related papers, either for further research or to provide a source for our claims. This is just a brief intro into what Exa can do. For a look at how you can leverage getting full contents, check out [this article](https://docs.exa.ai/reference/contents).
