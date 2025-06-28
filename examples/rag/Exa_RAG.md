# RAG: Answer your questions with context

LLMs are powerful because they compress large amounts of data and patterns into a format that allows convenient access, but this compressions isn't lossless. Exa can bring the most relevant data into context. This lets us to combine the compressed data of the LLM with a select quantity of uncompressed data for the problem at hand for the best generations possible.

Exa's SDKs make incorporating quality data into your LLM pipelines quick and painless. Install the SDK by running this command in your terminal:

`pip install exa-py`


```python
# Now, import the Exa class and pass your API key to it.
from exa_py import Exa

my_exa_api_key = "YOUR_API_KEY_HERE"
exa = Exa(my_exa_api_key)
```

For our first example, we'll set up Exa to answer questions with OpenAI's popular GPT 3.5 model. (You can use GPT 4 or another model if you prefer!) We'll use Exa's `highlight` feature, which directly returns relevant text of customizable length for a query. You'll need to run `pip install openai` to get access to OpenAI's SDK if you haven't used it before. More information about the OpenAI python SDK can be found [here](https://platform.openai.com/docs/quickstart?context=python).


```python
# Set up OpenAI' SDK
from openai import OpenAI

openai_api_key = "YOUR_API_KEY_HERE"
openai_client = OpenAI(api_key=openai_api_key)
```

Now, we just need some questions to answer!


```python
questions = [
    "How did bats evolve their wings?",
    "How did Rome defend Italy from Hannibal?",
]
```

While LLMs can answer some questions on their own, they have limitations:
- LLMs don't have knowledge past when their training was stopped, so they can't know about recent events
- If an LLM doesn't know the answer, it will often 'hallucinate' a correct-sounding response, and it can be difficult and inconvenient to distinguish these from correct answers
- Because of the opaque manner of generation and the problems mentioned above, it is difficult to trust an LLM's responses when accuracy is [important](https://www.forbes.com/sites/mollybohannon/2023/06/08/lawyer-used-chatgpt-in-court-and-cited-fake-cases-a-judge-is-considering-sanctions/?sh=27194eb67c7f)

Robust retrieval helps solve all of these issues by providing a quality sources of ground truth for the LLM (and their human users) to leverage. Let's use Exa to get some information about our questions:


```python
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
```


```python
info_for_llm
```




    [['As the only mammals with powered flight, the evolutionary\xa0history of their wings has been poorly understood. However, research published Monday in Nature and PLoS Genetics has provided the first comprehensive look at the genetic origins of their incredible wings.But to appreciate the genetics of their wing development, it’s important to know how crazy a bat in flight truly\xa0looks.Try a little experiment: Stick your arms out to the side, palms facing forward, thumbs pointing up toward the ceiling. Now imagine that your fingers are\xa0long, arching down toward the floor like impossibly unkempt fingernails — but still made of bone, sturdy and spread apart. Picture the sides of your body connecting to your hands, a rubbery membrane attaching your leg and torso to those long fingers, binding you with strong, stretchy skin. Then, finally, imagine using your muscles to flap those enormous hands.Bats, man.As marvelous as bat flight is to behold, the genetic origins of their storied wings has remained murky. However, new findings from an international team of researchers led by Nadav Ahituv, PhD, of the University of California at San Francisco, Nicola Illing, PhD, of the University of Cape Town\xa0in\xa0South Africa\xa0and Katie Pollard, PhD of the UCSF-affiliated Gladstone Institutes has shed new light on how, 50 million years ago, bats took a tetrapod blueprint for arms and legs and went up into the sky.Using a sophisticated set of genetic tools, researchers approached the question of how bats evolved flight by looking not only at which genes were used in the embryonic development of wings, but at what point during development the genes were turned on and off, and — critically — what elements in the genome were regulating the expression of these genes. Genes do not just turn themselves on without input; genetic switches, called enhancers, act to regulate the timing and levels of gene expression in the body.',
      "Since flight evolved millions of years ago in all of the groups  that are capable of flight today, we can't observe the changes in behavior and much of the  morphology that the evolution of flight involves. We do have the fossil record, though, and  it is fairly good for the three main groups that evolved true flight. We'll spare you an in-depth description of how each group evolved flight for now;  see the later exhibits for a description of each group and how they developed flight.",
      "It's easy to forget that one in five species of mammal on this planet have wings capable of delivering spectacularly acrobatic flying abilities. Equally incredibly, two-thirds of these 1,200 species of flying mammal can fly in the dark, using exquisite echolocation to avoid obstacles and snatch airborne prey with stunning deftness. These amazing feats have helped make bats the focus not only of folkloric fascination, but also of biological enquiry and mimicry by human engineers from Leonardo da Vinci onwards. Recent research in PLOS journals continues to add surprising new findings to what we know about bats, and how they might inspire us to engineer manmade machines such as drones to emulate their skills. Bats, unlike most birds and flying insects, have relatively heavy wings – something that might appear disadvantageous. But a recent study in PLOS Biology by Kenny Breuer and colleagues shows that bats can exploit the inertia of the wings to make sharp turns that would be near-impossible using aerodynamic forces alone. The authors combined high-speed film of real bats landing upside-down on ceiling roosts with computational modelling to tease apart aerodynamic and inertial effects."],
     ["things, gold and silver, could buy a victory. And this Other Italian cities, inspired by Rome's example, overpowered occupying troops, shut their gates again and invited a second siege. Hannibal could not punish them without dividing his he had no competent leadership to do so, what with one member of",
      'A group of Celts known as the Senone was led through Italy by their commander, Brennus. The Senone Gauls were threatening the nearby town of Clusium, when Roman Ambassadors from the Fabii family were sent to negotiate peace for Clusium. The Romans were notoriously aggressive, and so it is only a little surprising that when a scuffle broke out between the Gauls and Clusians, the Fabii joined in and actually killed a Senone chieftain. The Roman people voted to decide the fate of those who broke the sacred conduct of ambassadors, but the Fabii were so popular that they were instead voted to some of the highest positions in Rome. This absolutely infuriated Brennus and his people and they abandoned everything and headed straight for Rome. Rome was woefully unprepared for this sudden attack. The Gauls had marched with purpose, declaring to all the towns they passed that they would not harm them, they were heading straight for Rome.',
      "Hannibal had no intention to sit and recieve the romans in spain.Hannibal clearly considered the nature of roman power-and came to the conclusion that Rome could only be defeated in Italy.The cornerstone of Rome's power was a strategic manpower base that in theory could produce 7,00,000 infantry and 70,000 cavalry.More than half of this manpower base (4,00,000) was provided by rome's Italian allies,who paid no taxes but had to render military service to rome's armies.Not all were content.Carthage on the other hand rarely used its own citizens for war,bulk of its army being mercenaries.In any case its manpower could never even come close to Rome,the fact that had aided roman victory in the 1st Punic war.Hannibal thus understood that Rome could afford to raise and send army after army to spain and take losses. Meanwhile any carthiginian losses in spain would encourage the recently conquered iberian tribes to defect. The only way to defeat Rome,was to fight in italy itself.By winning battle after battle on italian soil and demonstrating to the italian allies rome's inability to protect them and weakness,he could encourage them to break free of Rome eroding Rome's manpower to sizeable proportions. But there was one problem,his fleet was tiny and Rome ruled the seas.By land,the coastal route would be blocked by Roman forces and her ally-the great walled city of massalia.Hannibal thus resolved to think and do the impossible - move thousands of miles by land through the pyranees mountains,uncharted territory inhabited by the fierce gauls ,then through the Alps mountains and invade italy. Even before the siege of Saguntum had concluded,Hannibal had set things in motion.Having sent a number of embassies to the Gallic tribes in the Po valley with the mission of establishing a safe place for Hannibal to debouch from the Alps into the Po valley. He did not desire to cross this rugged mountain chain and to descend into the Po valley with exhausted troops only to have to fight a battle.Additionally the fierce gauls would provide a source of manpower for Hannibal's army.The romans had recently conquered much territory from the gauls in this area,brutally subjagating them ,seizing their land and redistributing it to roman colonists.Thus securing an alliance proved to be easy. After the sack of Saguntum he dismissed his troops to their own localities."]]



Now, let's give the context we got to our LLM so it can answer our questions with solid sources backing them up!


```python
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
```


```python
from pprint import pprint # pretty print
pprint(responses)
```

    ['\n'
     '  Question: How did bats evolve their wings?\n'
     '  Answer: Recent research has shed new light on how bats evolved their '
     'wings. An international team of researchers used genetic tools to study the '
     'embryonic development of bat wings and the genes involved in their '
     'formation. They also investigated the regulatory elements in the genome that '
     'control the expression of these genes. By analyzing these factors, the '
     'researchers discovered that bats took a tetrapod blueprint for arms and legs '
     'and adapted it to develop wings, allowing them to fly. This research '
     'provides a comprehensive understanding of the genetic origins of bat wings '
     'and how they evolved over 50 million years ago.\n'
     '  ',
     '\n'
     '  Question: How did Rome defend Italy from Hannibal?\n'
     '  Answer: Rome defended Italy from Hannibal by using various strategies. One '
     'of the main defenses relied on the Roman manpower base, which consisted of a '
     'large army made up of Roman citizens and Italian allies who were obligated '
     "to render military service. Rome's strategic manpower base was a cornerstone "
     'of their power, as it could produce a significant number of infantry and '
     'cavalry. This posed a challenge for Hannibal, as Carthage relied heavily on '
     "mercenaries and could not match Rome's manpower.\n"
     '\n'
     'Hannibal realized that in order to defeat Rome, he needed to fight them in '
     'Italy itself. His plan was to win battles on Italian soil and demonstrate '
     "Rome's inability to protect their Italian allies, with the intention of "
     "encouraging them to break free from Rome. This would erode Rome's manpower "
     'base to a sizeable proportion. However, Hannibal faced several obstacles. '
     'Rome ruled the seas, making it difficult for him to transport troops and '
     'supplies by sea. Additionally, the coastal route to Italy would be blocked '
     'by Roman forces and their ally, the walled city of Massalia.\n'
     '\n'
     'To overcome these challenges, Hannibal devised a daring plan. He decided to '
     'lead his troops on a treacherous journey through the Pyrenees mountains, '
     'inhabited by fierce Gauls, and then through the Alps mountains to invade '
     'Italy. He sent embassies to Gallic tribes in the Po valley, securing '
     'alliances and establishing a safe place for his army to enter the Po valley '
     'from the Alps.\n'
     '\n'
     'Overall, Rome defended Italy from Hannibal by leveraging their manpower '
     'base, their control of the seas, and their strategic alliances with Italian '
     'allies. They also had the advantage of better infrastructure and control '
     'over resources within Italy itself. These factors ultimately played a '
     "significant role in Rome's defense against Hannibal's invasion.\n"
     '  ']


Exa can be used for more than simple question answering. One superpower of embeddings-based search is that we can search for the meaning for sentences or even paragraphs:


```python
paragraph = """Georgism, also known as Georgism, is an economic philosophy and ideology named after the American political economist Henry George (1839–1897). This doctrine advocates for the societal collective, rather than individual property owners, to capture the economic value derived from land and other natural resources. To this end, Georgism proposes a single tax on the unimproved value of land, known as a "land value tax," asserting that this would deter speculative land holding and promote efficient use of valuable resources. Adherents argue that because the supply of land is fundamentally inelastic, taxing it will not deter its availability or use, unlike other forms of taxation. Georgism differs from Marxism and capitalism, underscoring the distinction between common and private property while largely contending that individuals should own the fruits of their labor."""
query = f"The best academic source about {paragraph} is (paper: "
georgism_search_response = exa.search_and_contents(paragraph, highlights=highlights_options, num_results=5, use_autoprompt=False)
```


```python
for result in georgism_search_response.results:
    print(result.title)
    print(result.url)
    pprint(result.highlights)
```

    Henry George
    https://www.newworldencyclopedia.org/entry/Henry_George
    ["George's theory of interest is nowadays dismissed even by some otherwise "
     'Georgist authors, who see it as mistaken and irrelevant to his ideas about '
     'land and free trade. The separation of the value of land into improved and '
     "unimproved is problematic in George's theory. Once construction has taken "
     'place, not only the land on which such improvements were made is affected, '
     'the value of neighboring, as yet unimproved, land is impacted. Thus, while '
     'the construction of a major attraction nearby may increase the value of '
     'land, the construction of factories or nuclear power plants decreases its '
     'value. Indeed, location is the single most important asset in real estate. '
     'George intended to propose a tax that would have the least negative impact '
     'on productive activity. However, even unimproved land turns out to be '
     'affected in value by productive activity in the neighborhood.']
    Wikiwand
    https://www.wikiwand.com/en/Georgism
    ['Georgism is concerned with the distribution of economic rent caused by land '
     'ownership, natural monopolies, pollution rights, and control of the commons, '
     'including title of ownership for natural resources and other contrived '
     'privileges (e.g. intellectual property). Any natural resource which is '
     'inherently limited in supply can generate economic rent, but the classical '
     'and most significant example of land monopoly involves the extraction of '
     'common ground rent from valuable urban locations. Georgists argue that '
     'taxing economic rent is efficient, fair and equitable. The main Georgist '
     'policy recommendation is a tax assessed on land value, arguing that revenues '
     'from a land value tax (LVT) can be used to reduce or eliminate existing '
     'taxes (such as on income, trade, or purchases) that are unfair and '
     'inefficient. Some Georgists also advocate for the return of surplus public '
     "revenue to the people by means of a basic income or citizen's dividend. The "
     'concept of gaining public revenues mainly from land and natural resource '
     'privileges was widely popularized by Henry George through his first book, '
     'Progress and Poverty (1879).']
    Henry George
    https://www.conservapedia.com/Henry_George
    ['He argued that land, unlike other factors of production, is supplied by '
     'nature and that rent is unearned surplus. The landless deserve their share '
     'of this surplus as a birthright, according to George. Henry George was born '
     'in Philadelphia, Pennsylvania, on the 2nd of September 1839. He settled in '
     'California in 1858; then later removed to New York in 1880; was first a '
     'printer, then an editor, but finally devoted all his life to economic and '
     'social questions. In 1860, George met Annie Corsina Fox. Her family was very '
     'opposed to the relationship, and in 1861 they eloped. In 1871 he published '
     'Our Land Policy, which, as further developed in 1879 under the title of '
     'Progress and Poverty, speedily attracted the widest attention both in '
     'America and in Europe.']
    Georgism - Wikipedia
    https://en.wikipedia.org/wiki/Georgism
    ['A key issue to the popular adoption of Georgism is that homes are illiquid '
     'yet governments need cash every year. Some economists have proposed other '
     'ways of extracting value from land such as building government housing and '
     'selling homes to new buyers in areas of fast-rising land value. The '
     'government would theoretically collect revenue from home sales without much '
     'cost to current homeowners while slowing down land value appreciation in '
     'high-demand areas. Henry George, whose writings and advocacy form the basis '
     'for Georgism Georgist ideas heavily influenced the politics of the early '
     '20th century. Political parties that were formed based on Georgist ideas '
     'include the Commonwealth Land Party in the United States, the Henry George '
     'Justice Party in Victoria, the Single Tax League in South Australia, and the '
     "Justice Party in Denmark. In the United Kingdom, George's writings were "
     'praised by emerging socialist groups in 1890s such as the Independent Labour '
     'Party and the Fabian Society, which would each go on to help form the '
     'modern-day Labour Party.']
    Georgism
    https://rationalwiki.org/wiki/Georgism
    ['Even with mostly primitive methods, land values are already assessed around '
     'the world wherever property/council taxes exist, and some municipalities '
     'even collect all their revenue from land values. Though these are '
     'market-based measures, they can still prove difficult and require upfront '
     'investment. Georgists believe that the potential value of land is greater '
     'than the current sum of government spending, since the abolition of taxes on '
     'labor and investment would further increase the value of land. Conversely, '
     'the libertarian strain in Georgism is evident in the notion that their land '
     'tax utopia also entails reducing or eliminating the need for many of the '
     'things governments currently supply, such as welfare, infrastructure to '
     'support urban sprawl, and military & foreign aid spending to secure '
     "resources abroad. Therefore, many Georgists propose a citizen's dividend. "
     'This is a similar concept to basic income but its proponents project its '
     'potential to be much larger due to supposedly huge takings from the land '
     'tax, combined with lowered government spending. It has been recognized since '
     'Adam Smith and David Ricardo that a tax on land value itself cannot be '
     'passed on to tenants, but instead would be paid for by the owners of the '
     'land:']


Using Exa, we can easily find related papers, either for further research or to provide a source for our claims. This is just a brief intro into what Exa can do. For a look at how you can leverage getting full contents, check out [this article](https://docs.exa.ai/reference/contents).
