from flask import Flask, request, render_template_string, send_file, jsonify
import os
import uuid
from werkzeug.utils import secure_filename
from xml.etree import ElementTree as ET
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
import io

app = Flask(__name__)
app.config['UPLOAD_ARQ'] = 'uploads'
app.config['PDF_ARQ'] = 'pdfs'
os.makedirs(app.config['UPLOAD_ARQ'], exist_ok=True)
os.makedirs(app.config['PDF_ARQ'], exist_ok=True)

# HTML dessa desgraça
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Lista de Produtos NF-e</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; background: white; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); overflow: hidden; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }
        .upload-area { border: 3px dashed #ddd; border-radius: 10px; padding: 40px; text-align: center; margin: 30px; transition: all 0.3s; cursor: pointer; }
        .upload-area:hover { border-color: #667eea; background: #f8f9ff; }
        .upload-area.dragover { border-color: #667eea; background: #e8ecff; }
        input[type="file"] { display: none; }
        .upload-btn { background: #667eea; color: white; padding: 12px 30px; border: none; border-radius: 25px; font-size: 16px; cursor: pointer; transition: all 0.3s; }
        .upload-btn:hover { background: #5a67d8; transform: translateY(-2px); }
        .download-btn { position: fixed; top: 20px; left: 20px; background: #48bb78; color: white; padding: 12px 20px; border: none; border-radius: 25px; font-size: 14px; cursor: pointer; box-shadow: 0 4px 15px rgba(72,187,120,0.4); transition: all 0.3s; z-index: 1000; }
        .download-btn:hover { background: #38a169; transform: translateY(-2px); }
        .download-btn.hidden { display: none; }
        .results { padding: 30px; }
        .stats { display: flex; gap: 20px; margin-bottom: 30px; flex-wrap: wrap; }
        .stat-card { background: #f8f9ff; padding: 20px; border-radius: 10px; flex: 1; min-width: 150px; text-align: center; border-left: 5px solid #667eea; }
        .stat-number { font-size: 2em; font-weight: bold; color: #667eea; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
        th { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; text-align: left; font-weight: 600; }
        td { padding: 12px 15px; border-bottom: 1px solid #eee; word-break: break-word; }
        tr:nth-child(even) { background: #f8f9ff; }
        tr:hover { background: #e8ecff; }
        .loading { text-align: center; padding: 40px; font-size: 18px; color: #666; }
        .error { background: #fed7d7; color: #c53030; padding: 20px; border-radius: 10px; margin: 20px; border-left: 5px solid #e53e3e; }
        @media (max-width: 768px) { 
            .stats { flex-direction: column; } 
            table { font-size: 14px; } 
            th, td { padding: 10px 8px; } 
            .container { margin: 10px; }
        }
    </style>
</head>
<body>
    <button id="downloadBtn" class="download-btn hidden" onclick="downloadPDF()">📥 Download PDF</button>
    
    <div class="container">
        <div class="header">
            <h1>📋 Lista de Produtos NF-e</h1>
            <p>Faça upload do arquivo XML para visualizar os produtos</p>
        </div>
        
        <div class="upload-area" id="uploadArea">
            <input type="file" id="xmlFile" accept=".xml" />
            <button class="upload-btn" onclick="document.getElementById('xmlFile').click()">
                📁 Escolher Arquivo XML
            </button>
            <p style="margin-top: 15px; color: #666;">ou arraste o arquivo aqui</p>
        </div>
        
        <div id="results" class="results" style="display: none;">
            <!-- Conteúdo será inserido via JavaScript -->
        </div>
    </div>

    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('xmlFile');
        const resultsDiv = document.getElementById('results');
        const downloadBtn = document.getElementById('downloadBtn');

        ['dragover', 'dragenter'].forEach(event => {
            uploadArea.addEventListener(event, (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadArea.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(event => {
            uploadArea.addEventListener(event, (e) => {
                e.preventDefault();
                e.stopPropagation();
                uploadArea.classList.remove('dragover');
            });
        });

        uploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                uploadFile();
            }
        });

        fileInput.addEventListener('change', uploadFile);

        function uploadFile() {
            const file = fileInput.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('xml_file', file);

            uploadArea.style.display = 'none';
            resultsDiv.innerHTML = '<div class="loading">⏳ Processando arquivo...</div>';
            resultsDiv.style.display = 'block';

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    displayResults(data.produtos, data.total);
                    downloadBtn.dataset.nomearquivo = data.nomearquivo;
                    downloadBtn.classList.remove('hidden');
                } else {
                    resultsDiv.innerHTML = `<div class="error">❌ Erro: ${data.error}</div>`;
                    uploadArea.style.display = 'block';
                }
            })
            .catch(error => {
                resultsDiv.innerHTML = '<div class="error">❌ Erro ao processar arquivo</div>';
                uploadArea.style.display = 'block';
                console.error('Erro:', error);
            });
        }

        function displayResults(produtos, total) {
            let html = `
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">${total.toLocaleString()}</div>
                        <div>Total de Produtos</div>
                    </div>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Cód. Prod.</th>
                            <th>Descrição</th>
                            <th>Valor Total</th>
                            <th>Qtd.</th>
                            <th>Valor Unit.</th>
                            <th>NCM</th>
                            <th>EAN</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            produtos.forEach((prod, index) => {
                html += `
                    <tr>
                        <td>${prod.cProd}</td>
                        <td>${prod.xProd.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</td>
                        <td>R$ ${parseFloat(prod.vProd).toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                        <td>${parseFloat(prod.qCom).toLocaleString()}</td>
                        <td>R$ ${parseFloat(prod.vUnCom).toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                        <td>${prod.NCM}</td>
                        <td>${prod.cEAN}</td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            resultsDiv.innerHTML = html;
        }

        function downloadPDF() {
            const nomearquivo = downloadBtn.dataset.nomearquivo;
            window.location.href = `/download/${nomearquivo}`;
        }
    </script>
</body>
</html>
"""

EXTENSAO = {'xml'}

def arquivo(nomearquivo):
    return '.' in nomearquivo and \
           nomearquivo.rsplit('.', 1)[1].lower() in EXTENSAO #INFERNO NA TERRA COMPREENDER ISSO

def parse_nfe_products(xml_conteudo): #lê e retorna os produtos na lista
    try:
        root = ET.fromstring(xml_conteudo.encode('utf-8'))
        portfis = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        produtos = []
        dets = root.findall('.//nfe:det', portfis)
        
        for det in dets:
            prod = det.find('nfe:prod', portfis)
            if prod is not None:
                product = {
                    'cProd': prod.get('cProd', 'N/A'),
                    'xProd': prod.get('xProd', 'N/A')[:100],  # Limita tamanho
                    'vProd': prod.get('vProd', '0.00'),
                    'qCom': prod.get('qCom', '0'),
                    'vUnCom': prod.get('vUnCom', '0.00'),
                    'NCM': prod.get('NCM', 'N/A'),
                    'cEAN': prod.get('cEAN', 'N/A')
                }
                produtos.append(product)
        return produtos
    except Exception as e:
        print(f"Erro parsing XML: {e}")
        return []

def create_pdf(produtos, nomearquivo): #cria o pdf
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], 
        fontSize=16, alignment=1, spaceAfter=30
    )
    
    story = [Paragraph("Lista de Produtos da NF-e", title_style), Spacer(1, 20)]
    
    headers = ['Cód. Prod.', 'Descrição', 'Valor Total', 'Qtd.', 'Valor Unit.', 'NCM', 'EAN'] #cria as lacuna
    chunk_size = 50
    
    for i in range(0, len(produtos), chunk_size): #len dos produtos e eu esqueci o resto aí, acho que é das colunas
        chunk = produtos[i:i + chunk_size]
        data = [headers]
        
        for prod in chunk:
            data.append([
                prod['cProd'],
                prod['xProd'][:40] + '...' if len(prod['xProd']) > 40 else prod['xProd'],
                f"R$ {prod['vProd']}",
                prod['qCom'],
                f"R$ {prod['vUnCom']}",
                prod['NCM'],
                prod['cEAN']
            ])
        
        table = Table(data, colWidths=[0.6*inch, 2.5*inch, 1*inch, 0.6*inch, 1*inch, 0.8*inch, 1*inch]) 
        #tabela pra colocar lacuna por coluna
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.lightgrey]),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE')
        ]))
        story.append(table)
        if i + chunk_size < len(produtos):
            story.append(Spacer(1, 0.5*inch))
    
    doc.build(story)
    buffer.seek(0)
    
    pdf_cam = os.path.join(app.config['PDF_ARQ'], f"{nomearquivo}.pdf") #retorna pra fazer o PF
    with open(pdf_cam, 'wb') as f:
        f.write(buffer.getvalue())
    return pdf_cam

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST']) #Não é HTML 
def upload_file():
    try:
        if 'xml_file' not in request.files: #não enviado
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})

        file = request.files['xml_file']
        if file.nomearquivo == '': #não selecionado
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})

        if file and arquivo(file.nomearquivo): #colocad 100%
            nomearquivo = str(uuid.uuid4()) #que poressa
            xml_path = os.path.join(app.config['UPLOAD_ARQ'], f"{nomearquivo}.xml")
            file.save(xml_path)
            
            with open(xml_path, 'r', encoding='utf-8', errors='ignore') as f:
                xml_conteudo = f.read()
            
            produtos = parse_nfe_products(xml_conteudo)
            pdf_cam = create_pdf(produtos, nomearquivo)
            
            # 
            os.remove(xml_path)
            
            return jsonify({
                'success': True,
                'produtos': produtos,
                'total': len(produtos),
                'nomearquivo': nomearquivo
            })
        return jsonify({'success': False, 'error': 'Arquivo XML inválido'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Erro: {str(e)}'})

@app.route('/download/<nomearquivo>') #Não achou
def download_pdf(nomearquivo): #Deu ruim no PDF
    pdf_cam = os.path.join(app.config['PDF_ARQ'], f"{nomearquivo}.pdf")
    if os.path.exists(pdf_cam):
        return send_file(pdf_cam, anexo=True, nom_down='produtos_nfe.pdf')
    return 'Arquivo PDF não encontrado', 404

if __name__ == '__main__':
    print("Servidor rodando em http://localhost:5000") #SEMPRE ESQUECIA O LOCALHOST
    app.run(debug=True, host='0.0.0.0', port=5000) #deixa o debug ativado nessa desgraça