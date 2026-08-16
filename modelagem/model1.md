Entender como integrar o **MCP (Model Context Protocol)** a um prompt tão complexo e estruturado quanto o que você compartilhou é um excelente passo para automatizar auditorias de qualidade.

O prompt que você forneceu foi desenhado para analisar uma transcrição que o usuário "cola" manualmente no chat, exigindo que a IA não utilize conhecimentos externos e gere um relatório rigoroso de 14 blocos e um JSON interno.

O **MCP** muda o jogo: ele permite que a IA se conecte diretamente aos sistemas do seu call center (como Zendesk, Genesys, Salesforce, bancos de dados) para buscar as transcrições sozinha e devolver os resultados para os seus dashboards, sem que um humano precise copiar e colar textos.

Abaixo, explico como adaptar esse cenário e apresento um fluxograma para facilitar a sua compreensão.

---

### ## Como usar o MCP com este Prompt

Para que este prompt funcione via MCP, você precisará configurar um **Servidor MCP** que possua ferramentas (tools) específicas. A IA usará o seu prompt como "instrução de sistema" e usará o MCP como suas "mãos" e "olhos" nos sistemas da empresa.

Aqui estão as 3 fases de integração:

#### 1. Fase de Entrada (Buscando a Transcrição)

Atualmente, a regra 1 do seu prompt diz: *"Ler toda a conversa. Não iniciar avaliações antes de terminar a leitura completa"*.
Com o MCP, você cria uma ferramenta chamada, por exemplo, `buscar_transcricao(protocolo)`.

* **Ação:** O usuário digita "Audite o protocolo 12345". A IA usa o MCP para acionar o banco de dados, que devolve o texto da conversa.
* **Atenção à Regra:** Como seu prompt exige que "Toda análise deve ser baseada exclusivamente na transcrição", o Servidor MCP deve garantir que retorne *apenas* a transcrição e os dados cadastrais estritamente necessários para aquela interação.



#### 2. Fase de Processamento (O Motor de Decisão)

Uma vez que o MCP entregou a transcrição para a IA, ela rodará o "Motor de Decisão" exatamente como está no seu prompt.

* Ela validará consistências, calculará o Score Operador e o Score Experiência.


* O uso do MCP aqui é invisível; a IA está apenas usando a sua capacidade de raciocínio sobre os dados que o MCP trouxe.

#### 3. Fase de Saída (Salvando o Relatório)

O seu prompt exige a geração de um relatório visual de 14 blocos e, internamente ou quando solicitado, um arquivo JSON.
Com o MCP, você pode criar uma ferramenta chamada `salvar_auditoria(json_dados, protocolo)`.

* **Ação:** Em vez de apenas imprimir o texto na tela, a IA aciona essa ferramenta para enviar o JSON gerado diretamente para o seu sistema de Business Intelligence (BI) ou banco de dados de Qualidade, alimentando os dashboards da operação.

---

### ## O que alterar no Prompt Original?

Para que o prompt saiba que possui ferramentas à disposição, você deve adicionar uma pequena instrução no início, logo após o papel de Especialista Sênior:

> **NOVA REGRA PARA MCP (Exemplo):**
> "Quando o usuário informar um número de protocolo, você deve obrigatoriamente utilizar a ferramenta `buscar_transcricao` para obter o texto do atendimento. Após realizar todas as análises lógicas e gerar o JSON estruturado, você deve utilizar a ferramenta `salvar_auditoria` para registrar os resultados no sistema, antes de imprimir o relatório visual de 14 blocos na tela."
> 
> 

---

### ## Fluxograma de Compreensão (Integração IA + MCP)

Aqui está a visualização do fluxo de trabalho ponta a ponta:

```text
┌───────────────────────┐
│   SISTEMAS DA EMPRESA │ (Telefonia, CRM, Chatbots)
└───────────┬───────────┘
            │ 1. Áudio é transcrito e salvo no banco
            v
┌───────────────────────┐
│     SERVIDOR MCP      │ <--- 2. Conecta as ferramentas aos seus sistemas
└───────────┬───────────┘
            │
            │ 3. Ferramenta: buscar_transcricao()
            │ 6. Ferramenta: salvar_auditoria()
            │
            v
┌───────────────────────┐      ┌──────────────────────────────────────────────┐
│  MODELO DE IA (LLM)   │ <--- │ PROMPT DE AUDITORIA (Seu arquivo)          │
│                       │      │ - Papel: Especialista Sênior[cite: 1]       │
│ 4. Analisa os dados   │      │ - Regra: Baseado só na transcrição[cite: 1] │
│ 5. Aplica cálculos e  │      │ - Saída: 14 Blocos Visuais + JSON[cite: 1]  │
│    validações         │      └──────────────────────────────────────────────┘
└───────────┬───────────┘
            │ 
            │ 7. IA devolve o relatório visual para o usuário
            v
┌───────────────────────┐
│        USUÁRIO        │ (Analista ou Gestor visualizando os 14 blocos)
└───────────────────────┘

```

**Resumo da Ópera:** O seu prompt é o "cérebro" que dita *como* pensar e avaliar. O MCP é a "ponte" que automatiza a entrada dos dados (para que você não tenha que copiar/colar) e automatiza a saída (para salvar o JSON gerado direto nos seus sistemas).