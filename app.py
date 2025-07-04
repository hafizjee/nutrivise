from flask import Flask, request, render_template, send_file, redirect
import requests
import json
import os
import csv

app = Flask(__name__)

MEMORY_FILE = "memory.json"
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump([], f)

def get_from_memory(query):
    with open(MEMORY_FILE, "r") as f:
        memory = json.load(f)
    for item in memory:
        if item["question"].strip().lower() == query.strip().lower():
            return item["answer"], None
    return None, None

def save_to_memory(question, answer):
    with open(MEMORY_FILE, "r+") as f:
        memory = json.load(f)
        memory.append({"question": question, "answer": answer})
        f.seek(0)
        json.dump(memory, f, indent=4)

def format_prompt(user_query):
    return (
        f"User: I have this issue: {user_query}\n"
        f"Please break the response into structured headings:\n"
        f"1. Affected Body Part\n2. Nutrient Deficiencies\n3. Recommended Foods\n4. Final Advice\n"
        f"Respond in clean readable markdown or HTML-like format.\n"
        f"Answer:"
    )

def call_openrouter(prompt):
    API_KEY = os.getenv("OPENROUTER_API_KEY")
    MODEL = "mistralai/mistral-7b-instruct"
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a helpful health assistant."},
            {"role": "user", "content": prompt}
        ]
    }

    try:
        print("Loaded API KEY:", API_KEY[:8] if API_KEY else "None")
        response = requests.post(url, headers=headers, json=payload)
        print("API Response Status:", response.status_code)
        print("API Response Text:", response.text)

        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
        else:
            return f"<p style='color:red;'>Error: {response.status_code} - {response.text}</p>"
    except Exception as e:
        print("API Call Exception:", str(e))
        return f"<p style='color:red;'>Exception occurred: {str(e)}</p>"

def format_response(text):
    sections = {
        "Affected Body Part": [],
        "Nutrient Deficiencies": [],
        "Recommended Foods": [],
        "Final Advice": []
    }
    current_section = None
    lines = text.strip().split('\n')

    for line in lines:
        line = line.strip()
        for key in sections.keys():
            if key.lower() in line.lower():
                current_section = key
        if current_section and line:
            sections[current_section].append(line)

    html = '<div class="response-box">'

    if len(sections["Affected Body Part"]) > 1:
        html += '<h4>🧠 <strong>Affected Body Part</strong></h4>'
        html += f'<p>{sections["Affected Body Part"][1]}</p>'
    elif sections["Affected Body Part"]:
        html += '<h4>🧠 <strong>Affected Body Part</strong></h4>'
        html += f'<p>{sections["Affected Body Part"][0]}</p>'

    if len(sections["Nutrient Deficiencies"]) > 1:
        html += '<h4>⚠️ <strong>Nutrient Deficiencies</strong></h4><ul>'
        for line in sections["Nutrient Deficiencies"][1:]:
            html += f'<li>{line}</li>'
        html += '</ul>'

    if len(sections["Recommended Foods"]) > 1:
        html += '<h4>🌿 <strong>Recommended Foods</strong></h4><ul>'
        for line in sections["Recommended Foods"][1:]:
            html += f'<li>{line}</li>'
        html += '</ul>'

    if len(sections["Final Advice"]) > 1:
        html += '<h4>🩺 <strong>Final Advice</strong></h4>'
        for line in sections["Final Advice"][1:]:
            html += f'<p>{line}</p>'
    elif sections["Final Advice"]:
        html += '<h4>🩺 <strong>Final Advice</strong></h4>'
        html += f'<p>{sections["Final Advice"][0]}</p>'

    html += '</div>'
    return html

@app.route("/", methods=["GET", "POST"])
def index():
    response = ""
    if request.method == "POST":
        query = request.form.get("symptom")
        if query:
            answer, _ = get_from_memory(query)
            if not answer:
                prompt = format_prompt(query)
                answer = call_openrouter(prompt)
                formatted_answer = format_response(answer)
                save_to_memory(query, formatted_answer)
                response = formatted_answer
            else:
                response = answer
    return render_template("index.html", response=response)

@app.route("/admin")
def admin_panel():
    with open(MEMORY_FILE, "r") as f:
        memory = json.load(f)
    return render_template("admin.html", memory=memory)

@app.route("/delete/<int:index>")
def delete_entry(index):
    with open(MEMORY_FILE, "r+") as f:
        memory = json.load(f)
        if 0 <= index < len(memory):
            del memory[index]
            f.seek(0)
            f.truncate()
            json.dump(memory, f, indent=4)
    return redirect("/admin")

@app.route("/export")
def export_csv():
    filename = "queries.csv"
    with open(MEMORY_FILE, "r") as f:
        memory = json.load(f)
    with open(filename, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["Question", "Answer"])
        for entry in memory:
            writer.writerow([entry["question"], entry["answer"]])
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
