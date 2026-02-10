from flask import Flask, request, render_template, send_file, jsonify
import os
import uuid
from xml.etree import ElementTree as ET
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors

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
                product = {
                    'cProd': prod.findtext('nfe:cProd', default='N/A', namespaces=ns),
                    'xProd': prod.findtext('nfe:xProd', default='N/A', namespaces=ns),
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
    doc = SimpleDocTemplate(pdf_cam, pagesize=A4, rightMargin=1*cm, leftMargin=1*cm, topMargin=1*cm, bottomMargin=1*cm)
    styles = getSampleStyleSheet()
    
    style_celula = ParagraphStyle('style_celula', fontSize=8, leading=10)
    style_header = ParagraphStyle('style_header', fontSize=9, textColor=colors.whitesmoke, fontName='Helvetica-Bold', alignment=1)
    
    story = [Paragraph("Lista de Produtos da NF-e", styles['Title']), Spacer(1, 20)]
    
    data = [[
        Paragraph("Cód.", style_header), Paragraph("Descrição", style_header), 
        Paragraph("Total", style_header), Paragraph("Qtd.", style_header), 
        Paragraph("Unit.", style_header), Paragraph("NCM", style_header), Paragraph("EAN", style_header)
    ]]
    
    for p in produtos:
        data.append([
            Paragraph(p['cProd'], style_celula),
            Paragraph(p['xProd'], style_celula), 
            Paragraph(f"R$ {float(p['vProd']):.2f}", style_celula),
            Paragraph(p['qCom'], style_celula),
            Paragraph(f"R$ {float(p['vUnCom']):.2f}", style_celula),
            Paragraph(p['NCM'], style_celula),
            Paragraph(p['cEAN'], style_celula)
        ])
    
    table = Table(data, colWidths=[1.8*cm, 6.5*cm, 2.2*cm, 1.2*cm, 2.2*cm, 1.8*cm, 2.8*cm]) 
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#667eea")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9ff")])
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
        file = request.files.get('xml_file')
        if file and arquivo(file.filename): #colocad 100$
            nome_unico = str(uuid.uuid4())
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
    app.run(debug=True) #deixa o debug ativado
