import os
import re
from docx import Document
import pypdf
app = Flask(__name__)
# Basic layout template using pure modern CSS (Tailwind CDN)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enterprise Resume Intelligence Sorter</title>
    <script src="https://jsdelivr.net"></script>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen p-8">
    <div class="max-w-5xl mx-auto bg-white shadow-xl rounded-2xl p-8 border border-slate-100">
        <header class="mb-8 border-b border-slate-100 pb-6">
            <h1 class="text-3xl font-extrabold text-slate-900 tracking-tight">💼 Enterprise Resume Sorter</h1>
            <p class="text-slate-500 mt-2">Scale automated hiring pipelines with advanced text extraction and contextual semantic matching.</p>
        </header>
        <form id="uploadForm" enctype="multipart/form-data" class="space-y-6">
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-2">Target Job Profile Keywords (Comma-separated)</label>
                <textarea name="keywords" required rows="3" class="w-full rounded-xl border border-slate-200 p-4 focus:outline-none focus:ring-2 focus:ring-blue-500 transition" placeholder="e.g., Python, Kubernetes, System Design, React, AWS, Team Leadership"></textarea>
            </div>
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-2">Upload Candidate Resumes (.pdf, .docx, .txt)</label>
                <div class="border-2 border-dashed border-slate-200 rounded-xl p-8 text-center bg-slate-50 hover:bg-slate-100/50 transition cursor-pointer relative">
                    <input type="file" name="resumes" multiple accept=".pdf,.docx,.txt" required class="absolute inset-0 w-full h-full opacity-0 cursor-pointer">
                    <p class="text-slate-500 text-sm font-medium">Drag & drop files here, or click to browse local storage</p>
                    <p class="text-xs text-slate-400 mt-1">Supports batch multi-upload up to dozens of candidates simultaneously</p>
                </div>
            </div>
            <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3.5 px-6 rounded-xl transition shadow-md shadow-blue-200 flex items-center justify-center gap-2 cursor-pointer">
                <span>Analyze & Rank Candidates</span>
            </button>
        </form>
        <!-- Loader State -->
        <div id="loader" class="hidden my-12 text-center">
            <div class="inline-block w-8 h-8 border-4 border-slate-200 border-t-blue-600 rounded-full animate-spin mb-2"></div>
            <p class="text-slate-500 text-sm font-medium">Extracting documents and indexing keywords...</p>
        </div>
        <!-- Results Table -->
        <div id="resultsWrapper" class="hidden mt-12 animate-fade-in">
            <h2 class="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">
                📊 Evaluation Leaderboard
            </h2>
            <div class="overflow-x-auto border border-slate-100 rounded-xl">
                <table class="w-full border-collapse bg-white text-left text-sm text-slate-500">
                    <thead class="bg-slate-50 text-xs font-semibold uppercase tracking-wider text-slate-700">
                        <tr>
                            <th class="px-6 py-4">Rank</th>
                            <th class="px-6 py-4">Candidate File</th>
                            <th class="px-6 py-4">Match Profile Score</th>
                            <th class="px-6 py-4">Identified Competencies</th>
                        </tr>
                    </thead>
                    <tbody id="resultsBody" class="divide-y divide-slate-100 border-t border-slate-100">
                        <!-- Populated via Javascript dynamically -->
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <script>
        document.getElementById('uploadForm').addEventListener('submit', async (e) => {
            e.preventDefault();            
            const loader = document.getElementById('loader');
            const resultsWrapper = document.getElementById('resultsWrapper');
            const resultsBody = document.getElementById('resultsBody');            
            loader.classList.remove('hidden');
            resultsWrapper.classList.add('hidden');
            resultsBody.innerHTML = '';
            try {
                const formData = new FormData(e.target);
                const response = await fetch('/api/sort-resumes', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();                
                if (!response.ok) throw new Error(data.error || 'Server processing failed');
                data.results.forEach((candidate, idx) => {
                    const row = document.createElement('tr');
                    row.className = "hover:bg-slate-50/70 transition";                    
                    const scoreColor = candidate.score >= 70 ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 
                                       candidate.score >= 40 ? 'bg-amber-50 text-amber-700 border-amber-200' : 
                                       'bg-rose-50 text-rose-700 border-rose-200';
                    row.innerHTML = `
                        <td class="px-6 py-4 font-bold text-slate-900">#${idx + 1}</td>
                        <td class="px-6 py-4 font-medium text-slate-700 max-w-xs truncate">${candidate.filename}</td>
                        <td class="px-6 py-4">
                            <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${scoreColor}">
                                ${candidate.score}% Match
                            </span>
                        </td>
                        <td class="px-6 py-4">
                            <div class="flex flex-wrap gap-1.5 max-w-md">
                                ${candidate.matched_keywords.map(kw => `<span class="bg-slate-100 text-slate-600 border border-slate-200 px-2 py-0.5 rounded text-xs">${kw}</span>`).join('') || '<span class="text-slate-400 italic text-xs">No key skill matches found</span>'}
                            </div>
                        </td>
                    `;
                    resultsBody.appendChild(row);
                });
                resultsWrapper.classList.remove('hidden');
            } catch (err) {
                alert('Error: ' + err.message);
            } finally {
                loader.classList.add('hidden');
            }
        });
    </script>
</body>
</html>
'''

def extract_text_from_pdf(file_stream):
    try:
        reader = pypdf.PdfReader(file_stream)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        return text
    except Exception:
        return ""
def extract_text_from_docx(file_stream):
    try:
        doc = Document(file_stream)
        return "\n".join([p.text for p in doc.paragraphs])
    except Exception:
        return ""
@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE)
@app.route('/api/sort-resumes', methods=['POST'])
def sort_resumes():
    keywords_raw = request.form.get('keywords', '')
    files = request.files.getlist('resumes')
    if not keywords_raw or not files or files[0].filename == '':
        return jsonify({"error": "Missing keywords or input resume files"}), 400
       keywords = [kw.strip().lower() for kw in keywords_raw.split(',') if kw.strip()]
    results = []
    for file in files:
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        text_content = ""
        if ext == '.txt':
            text_content = file.read().decode('utf-8', errors='ignore')
        elif ext == '.pdf':
            text_content = extract_text_from_pdf(file)
        elif ext == '.docx':
            text_content = extract_text_from_docx(file)
        else:
            continue
        text_content_lower = text_content.lower()
        matched_keywords = []
        for kw in keywords:
            pattern = r'\b' + re.escape(kw) + r'\b'
            if re.search(pattern, text_content_lower):
                matched_keywords.append(kw)
                score = 0
        if keywords:
            score = round((len(matched_keywords) / len(keywords)) * 100)
        results.append({
            "filename": filename,
            "score": score,
            "matched_keywords": [kw for kw in keywords if kw in matched_keywords]
        })
    results.sort(key=lambda x: x['score'], reverse=True)
    return jsonify({"results": results})
if __name__ == '__main__':
    app.run(debug=True, port=5000)