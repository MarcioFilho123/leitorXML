from flask import Flask, request, render_template, send_file, jsonify
import os
import uuid
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

EXTENSAO = {'xml'}

def arquivo(nomearquivo):
    return '.' in nomearquivo and nomearquivo.rsplit('.', 1)[1].lower() in EXTENSAO     # INFERNO NA TERRA COMPREENDER ISSO

def parse_nfe_products(xml_conteudo): #lê e retorna os produtos na lista
    try: #achatag
        root = ET.fromstring(xml_conteudo)
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
        produtos = []
        dets = root.findall('.//nfe:det', ns)
        
        for det in dets:
            prod = det.find('nfe:prod', ns)
            if prod is not None:
                #achou
                product = {
                    'cProd': prod.findtext('nfe:cProd', default='N/A', namespaces=ns),
                    'xProd': prod.findtext('nfe:xProd', default='N/A', namespaces=ns)[:100],
                    'vProd': prod.findtext('nfe:vProd', default='0.00', namespaces=ns),
                    'qCom': prod.findtext('nfe:qCom', default='0', namespaces=ns),
                    'vUnCom': prod.findtext('nfe:vUnCom', default='0.00', namespaces=ns),
                    'NCM': prod.findtext('nfe:NCM', default='N/A', namespaces=ns),
                    'cEAN': prod.findtext('nfe:cEAN', default='N/A', namespaces=ns)
                }
                produtos.append(product)
        return produtos
    except Exception as e:
        print(f"Erro parsing XML: {e}")
        return []

def create_pdf(produtos, nomearquivo): #cria o pdf
    pdf_cam = os.path.join(app.config['PDF_ARQ'], f"{nomearquivo}.pdf")
    doc = SimpleDocTemplate(pdf_cam, pagesize=A4)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], 
        fontSize=16, alignment=1, spaceAfter=30
    )
    
    story = [Paragraph("Lista de Produtos da NF-e", title_style), Spacer(1, 20)]
    headers = ['Cód.', 'Descrição', 'Valor Total', 'Qtd.', 'Unit.', 'NCM', 'EAN']
    
    data = [headers]
    for prod in produtos:
        data.append([
            prod['cProd'], 
            prod['xProd'][:40], # Corta pra não quebrar a tabela
            f"R$ {prod['vProd']}", 
            prod['qCom'], 
            f"R$ {prod['vUnCom'][:4]}", #é para seguir a regra 00.00 - PRECISA REVIZAR
            prod['NCM'], 
            prod['cEAN']
        ])
    
    table = Table(data, colWidths=[0.7*inch, 2.3*inch, 1*inch, 0.6*inch, 1*inch, 0.7*inch, 1*inch]) 
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.lightgrey])
    ]))
    story.append(table)
    doc.build(story)
    return pdf_cam

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST']) #Não é HTML 
def upload_file():
    try:
        if 'xml_file' not in request.files: #não enviado
            return jsonify({'success': False, 'error': 'Nenhum arquivo enviado'})
        
        file = request.files['xml_file']
        if file.filename == '': #não selecionado
            return jsonify({'success': False, 'error': 'Nenhum arquivo selecionado'})
        
        if file and arquivo(file.filename): #colocad 100$
            nome_unico = str(uuid.uuid4()) #
            xml_path = os.path.join(app.config['UPLOAD_ARQ'], f"{nome_unico}.xml")
            file.save(xml_path)
            
            with open(xml_path, 'rb') as f:
                produtos = parse_nfe_products(f.read())
            
            if not produtos: 
                return jsonify({'success': False, 'error': 'XML Vazio ou Sem produtos'})
    
            create_pdf(produtos, nome_unico)
            os.remove(xml_path)
            
            return jsonify({'success': True, 'produtos': produtos, 'total': len(produtos), 'nomearquivo': nome_unico})
        return jsonify({'success': False, 'error': 'Inválido'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/download/<nomearquivo>') #Não achou
def download_pdf(nomearquivo): #Deu ruim no PDF
    pdf_cam = os.path.join(app.config['PDF_ARQ'], f"{nomearquivo}.pdf")
    if os.path.exists(pdf_cam):
        return send_file(pdf_cam, as_attachment=True, download_name='produtos_nfe.pdf')
    return '404', 404

if __name__ == '__main__':
    print("Servidor rodando em http://localhost:5000") #SEMPRE ESQUECIA O LOCALHOST
    app.run(debug=True, host='0.0.0.0', port=5000) #deixa o debug ativado
