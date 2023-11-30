# Search with LLMs: Recent News Summarizer
---
In this example, we will build a LLM-based news summarizer app with the Metaphor API to keep us up-to-date with the latest news on a given topic.

This Jupyter notebook is available on [Colab](https://colab.research.google.com/drive/1WjttEBJBLuJc9Kavd9TGbdtup4rIOaRc?usp=sharing) for easy experimentation. You can also [check it out on Github](https://github.com/metaphorsystems/metaphor-python/tree/master/examples/newssummarizer/summarizer.ipynb), including a [plain Python version](https://github.com/metaphorsystems/metaphor-python/tree/master/examples/newssummarizer/summarizer.py) if you want to skip to a complete product.

To play with this code, first we need a [Metaphor API key](https://dashboard.metaphor.systems/overview) and an [OpenAI API key](https://platform.openai.com/api-keys). Get 1000 Metaphor searches per month free just for [signing up](https://dashboard.metaphor.systems/overview)!



```python
# install Metaphor and OpenAI SDKs
!pip install metaphor_python
!pip install openai
```


```python
from google.colab import userdata # comment this out if you're not using Colab

METAPHOR_API_KEY = userdata.get('METAPHOR_API_KEY') # replace with your api key, or add to Colab Secrets
OPENAI_API_KEY = userdata.get('OPENAI_API_KEY') # replace with your api key, or add to Colab Secrets
```

### First Approach (without Metaphor)
First, let's try building the app just by using the OpenAI API. We will use GPT 3.5-turbo as our LLM. Let's ask it for the recent news, like we might ask ChatGPT.


```python
import openai

openai.api_key = OPENAI_API_KEY

USER_QUESTION = "What's the recent news in physics this week?"

completion = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": USER_QUESTION},
    ],
)

response = completion.choices[0].message.content
print(response)
```

    One recent news in physics is the discovery of a new type of superconductor that operates at higher temperatures. Researchers at the University of Rochester and collaborator institutions have found a class of materials called "copper oxides" that can conduct electricity without any resistance at temperatures of -23 degrees Celsius (-9 degrees Fahrenheit). This finding could have significant implications for the development of more efficient energy transmission and storage systems.


Oh no! Since the LLM is unable to use recent data, it doesn't know the latest news. It might tell us some information, but that info isn't recent, and we can't be sure it's trustworthy either since it has no source. Luckily, Metaphor's API allows us to solve these problems by connecting our LLM app to the internet. Here's how:

### Second Approach (with Metaphor)

Let's use the Metaphor neural search engine to search the web for relevant links to the user's question.

First, we ask the LLM to generate a search engine query based on the question.


```python
import openai
from metaphor_python import Metaphor

openai.api_key = OPENAI_API_KEY
metaphor = Metaphor(METAPHOR_API_KEY)

SYSTEM_MESSAGE = "You are a helpful assistant that generates search queries based on user questions. Only generate one search query."
USER_QUESTION = "What's the recent news in physics this week?"

completion = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": USER_QUESTION},
    ],
)

search_query = completion.choices[0].message.content

print("Search query:")
print(search_query)
```

    Search query:
    "Recent breakthroughs in physics"


Looks good! Now let's put the search query into Metaphor. Let's also use `start_published_date` to filter the results to pages published in the last week:


```python
from datetime import datetime, timedelta

one_week_ago = (datetime.now() - timedelta(days=7))
date_cutoff = one_week_ago.strftime("%Y-%m-%d")

search_response = metaphor.search(
    search_query, use_autoprompt=True, start_published_date=date_cutoff
)

urls = [result.url for result in search_response.results]
print("URLs:")
for url in urls:
    print(url)
```

    URLs:
    https://phys.org/news/2023-11-carbon-material-energy-storage-advance-supercapacitors.html?utm_source=twitter.com&utm_medium=social&utm_campaign=v2%7C
    https://www.sciencedaily.com/releases/2023/11/231120124138.htm
    https://phys.org/news/2023-11-fullerene-like-molecule-metal-atoms.html?utm_source=twitter.com&utm_medium=social&utm_campaign=v2%7C
    https://arxiv.org/abs/2311.14088
    https://www.theguardian.com/science/2023/nov/24/amaterasu-extremely-high-energy-particle-detected-falling-to-earth
    https://phys.org/news/2023-11-physicists-evidence-exotic-quantum-material.html?utm_source=twitter.com&utm_medium=social&utm_campaign=v2%7C
    https://phys.org/news/2023-11-scientists-succeed-dolomite-lab-dissolving.html?utm_source=twitter.com&utm_medium=social&utm_campaign=v2%7C
    https://interestingengineering.com/science/strange-metal-quantum-shot-noise?utm_source=Twitter&utm_medium=content&utm_campaign=organic&utm_content=Nov24%7C
    https://arxiv.org/abs/2311.12903
    https://www.quantamagazine.org/meet-strange-metals-where-electricity-may-flow-without-electrons-20231127/


Now we're getting somewhere! Metaphor gave our app a list of relevant, useful URLs based on the original question.

By the way, we might be wondering what makes Metaphor special. Why can't we just search with Google? Well, [let's take a look for ourselves](https://www.google.com/search?q=Recent+news+in+physics+this+week) at the Google search results. It gives us the front page of lots of news aggregators, but not the news articles themselves. We can use Metaphor to skip writing a web crawler, and fetch the fresh content directly!

### Adding summarization
Okay, so we got a bunch of links. But we don't want to actually put the links into our browser, do we? That sounds like too much work. Our app should get the website contents for us and clean up the HTML.

Luckily Metaphor can do all that for us, and give us cleaned website contents for the search we just did in one command!


```python
contents_result = search_response.get_contents()

content_item = contents_result.contents[0]
print(f"{len(contents_result.contents)} items total, printing the first one:")
print(content_item)
```

    10 items total, printing the first one:
    ID: FVgU_DDBF1D6pqLlGS1qyg
    URL: https://phys.org/news/2023-11-carbon-material-energy-storage-advance-supercapacitors.html?utm_source=twitter.com&utm_medium=social&utm_campaign=v2%7C
    Title: New carbon material sets energy-storage record, likely to advance supercapacitors
    Extract: <div><div>
    <div>
    <figure>
    <figcaption>
     Conceptual art depicts machine learning finding an ideal material for capacitive energy storage. Its carbon framework (black) has functional groups with oxygen (pink) and nitrogen (turquoise). Credit: Tao Wang/ORNL, U.S. Dept. of Energy
     </figcaption> </figure>
    </div>
    <p>Guided by machine learning, chemists at the Department of Energy's Oak Ridge National Laboratory designed a record-setting carbonaceous supercapacitor material that stores four times more energy than the best commercial material. A supercapacitor made with the new material could store more energy—improving regenerative brakes, power electronics and auxiliary power supplies.
    	 
    	 </p>
    <p>"By combining a data-driven method and our research experience, we created a <a href="https://phys.org/tags/carbon+material/">carbon material</a> with enhanced physicochemical and electrochemical properties that pushed the boundary of energy storage for carbon supercapacitors to the next level," said chemist Tao Wang of ORNL and the University of Tennessee, Knoxville.
    </p><p>Wang led the study, titled "Machine-learning-assisted material discovery of oxygen-rich highly <a href="https://phys.org/tags/porous+carbon/">porous carbon</a> active materials for aqueous supercapacitor" and <a href="https://www.nature.com/articles/s41467-023-40282-1">published</a> in <i>Nature Communications</i>, with chemist Sheng Dai of ORNL and UTK.
    </p><p>"This is the highest recorded storage capacitance for porous carbon," said Dai, who conceived and designed the experiments with Wang. "This is a real milestone."
    </p><p>The researchers conducted the study at the Fluid Interface Reactions, Structures and Transport Center, or FIRST, an ORNL-led DOE Energy Frontier Research Center that operated from 2009 to 2022. Its partners at three national labs and seven universities explored fluid-solid interface reactions having consequences for capacitive electrical energy storage. Capacitance is the ability to collect and store <a href="https://phys.org/tags/electrical+charge/">electrical charge</a>.
    </p><p>When it comes to energy storage devices, batteries are the most familiar. They convert chemical energy to electrical energy and excel at storing energy. By contrast, capacitors store energy as an electric field, akin to static electricity. They cannot store as much energy as batteries in a given volume, but they can recharge repeatedly and do not lose the ability to hold a charge. Supercapacitors, such as those powering some electric buses, can store more charge than capacitors and charge and discharge more quickly than batteries.
    </p><p>Commercial supercapacitors have two electrodes—an anode and cathode—that are separated and immersed in an electrolyte. Double electrical layers reversibly separate charges at the interface between the electrolyte and the carbon. The materials of choice for making electrodes for supercapacitors are porous carbons. The pores provide a large surface area for storing the electrostatic charge.
    	 	 </p>
    <p>The ORNL-led study used <a href="https://phys.org/tags/machine+learning/">machine learning</a>, a type of artificial intelligence that learns from data to optimize outcomes, to guide the discovery of the superlative material. Runtong Pan, Musen Zhou and Jianzhong Wu from the University of California, Riverside, a FIRST partner university, built an artificial neural network model and trained it to set a clear goal: develop a "dream material" for energy delivery.
    </p><p>The model predicted that the highest capacitance for a carbon electrode would be 570 farads per gram if the carbon were co-doped with oxygen and nitrogen.
    </p><p>Wang and Dai designed an extremely porous doped carbon that would provide huge surface areas for interfacial electrochemical reactions. Then Wang synthesized the novel material, an oxygen-rich carbon framework for storing and transporting charge.
    </p><p>The carbon was activated to generate more pores and add functional chemical groups at sites for oxidation or reduction reactions. Industry uses activation agents such as potassium hydroxide that require a very high temperature, around 800°C, which drives oxygen from the material. Five years ago, Dai developed a process using sodium amide asAuthor: None


Awesome! That's really interesting, or it would be if we had bothered to read it all. But there's no way we're doing that, so let's ask the LLM to summarize it for us:


```python
import textwrap

SYSTEM_MESSAGE = "You are a helpful assistant that briefly summarizes the content of a webpage. Summarize the users input."

completion = openai.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": content_item.extract},
    ],
)

summary = completion.choices[0].message.content

print(f"Summary for {content_item.url}:")
print(content_item.title)
print(textwrap.fill(summary, 80))
```

    Summary for https://phys.org/news/2023-11-carbon-material-energy-storage-advance-supercapacitors.html?utm_source=twitter.com&utm_medium=social&utm_campaign=v2%7C:
    New carbon material sets energy-storage record, likely to advance supercapacitors
    Chemists at the Department of Energy's Oak Ridge National Laboratory have
    designed a carbonaceous supercapacitor material using machine learning that
    stores four times more energy than the best commercial material. The new
    material could improve regenerative brakes, power electronics, and auxiliary
    power supplies. The researchers used machine learning to guide the discovery of
    the material, which has enhanced physicochemical and electrochemical properties.
    The material has the highest recorded storage capacitance for porous carbon.


And we're done! We built an app that translates a question into a search query, uses Metaphor to search for useful links, uses Metaphor to grab clean content from those links, and summarizes the content to effortlessly answer your question about the latest news, or whatever we want.

We can be sure that the information is fresh, we have the source in front of us, and we did all this with a couple Metaphor queries and LLM calls, no web scraping or crawling needed!

**With Metaphor, we have empowered our LLM application with the Internet.** The possibilities are endless.
