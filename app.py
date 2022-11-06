import json
from flask import Flask, request, jsonify
import openai
from youtube_transcript_api import YouTubeTranscriptApi
import re
import urllib
from flask_cors import CORS, cross_origin

app = Flask(__name__)
cors = CORS(app)

openai.api_key = "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"


def clean_point(text):
    if text[0] == "-" or text[0] == "*":
        text = text[1:].strip()
    text = text.replace("\t", "")
    return

def process_text(text):
    points = []
    # first is usually just the line up to the next number
    cur_point = 1
    cur_str = f"{cur_point + 1}."
    while cur_str in text:
        ind = text.index(f"{cur_point + 1}.")
        point = text[:ind].strip()
        text = text[ind + len(cur_str) :]

        if len(point) == 0:
            continue
        point = clean_point(point)
        points.append(point)

        cur_point += 1
        cur_str = f"{cur_point + 1}."

    if len(points) == 0:
        return None
    return points


@app.route("/", methods=["POST"])
@cross_origin()
def to_notes():
    # STEP 1: GET YOUTUBE VIDEO TRANSCRIPT
    data = json.loads(request.data)
    transcript = YouTubeTranscriptApi.get_transcript(data["youtube_video"])

    complete_transcript = ""
    for t in transcript:
        complete_transcript = complete_transcript + t["text"]

    filter = "".join([chr(i) for i in range(1, 32)])

    params = {
        "format": "json",
        "url": "https://www.youtube.com/watch?v=%s" % data["youtube_video"],
    }
    url = "https://www.youtube.com/oembed"
    query_string = urllib.parse.urlencode(params)
    url = url + "?" + query_string

    with urllib.request.urlopen(url) as response:
        response_text = response.read()
        metadata = json.loads(response_text.decode())

    # STEP 2: SUMMARISE INTO BRIEF POINTS USING GPT-3
    prompt = f'''I was listening to a lecture with the following text:
	"""
	{complete_transcript.translate(str.maketrans('', '', filter))}
	"""
	It can be summarised in these 6 easy to understand bullet points:
	1.
	'''
    response = openai.Completion.create(
        prompt=prompt,
        engine="davinci",
        temperature=0.7,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0.1,
        best_of=1,
        max_tokens=260,
    )

    return {
        # "response":
        "response": {
            "notes": " ".join(re.findall(r'[^\r\n\t]+', response["choices"][0]["text"].strip())),
            "author": metadata["author_name"],
            "title": metadata["title"],
        }
    }


app.run(debug=True)
