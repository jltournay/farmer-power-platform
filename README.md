# The Farmer Power Cloud Platform

[![CI](https://github.com/jltournay/farmer-power-platform/actions/workflows/ci.yaml/badge.svg)](https://github.com/jltournay/farmer-power-platform/actions/workflows/ci.yaml)
![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/jltournay/9b8394c5dcef6340897ac07f62df408d/raw/coverage.json)

<!-- TOC -->
* [The Farmer Power Cloud Platform](#the-farmer-power-cloud-platform-)
  * [Context of this project](#context-of-this-project-)
  * [Executive summary](#executive-summary-)
  * [Functional Requirements](#functional-requirements-)
    * [The Plantation Model](#the-plantation-model-)
      * [Farm Data](#farm-data-)
      * [Factory Data](#factory-data-)
      * [Grading Model Data](#grading-model-data)
        * [Grading type](#grading-type)
        * [Attribute definitions](#attribute-definitions)
        * [Grading Rules](#grading-rules)
        * [Attribute Weights](#attribute-weights)
        * [Grade Thresholds](#grade-thresholds)
      * [Buyer Profile data](#buyer-profile-data-)
    * [The AI Model](#the-ai-model-)
    * [The Collection model](#the-collection-model-)
    * [The Knowledge Model](#the-knowledge-model-)
    * [The Action Plan model](#the-action-plan-model-)
    * [The Market Analysis Model](#the-market-analysis-model)
  * [Storage](#storage-)
    * [The document database](#the-document-database-)
    * [The Analyse database](#the-analyse-database-)
    * [The Action Plan database](#the-action-plan-database)
    * [The Plantation Model Database](#the-plantation-model-database-)
    * [The configuration Store](#the-configuration-store-)
<!-- TOC -->

## Context of this project 

FarmerPower.ai (https://farmerpower.ai) is an agritech startup transforming how tea factories manage quality, accountability, and market intelligence. Instead of relying on subjective grading after processing, the company uses an AI-powered camera system installed at the intake conveyor to evaluate green tea leaves in real time. This enables factories to instantly classify batches, optimize processing, and reduce waste, while providing growers with immediate feedback that drives better farming practices.
Beyond quality assessment, FarmerPower.ai integrates market analytics that connect factory data with auction and export performance. The system identifies which grades perform best in specific markets, helping factories tailor production, improve consistency, and capture higher prices. By linking on-farm data to market outcomes, the platform closes the loop between production and demand.
Through this digitized, data-driven approach, FarmerPower.ai enhances traceability, compliance, and fair value distribution across the supply chain. While tea is the initial focus, the technology is scalable to crops like coffee, grapes, and grains, positioning FarmerPower.ai as a pioneer in AI-driven quality and market intelligence for agriculture.


The Farmer Power solution is composed of three pillars:

1. **The Farmer Power QC Analyzer:** A cutting-edge, industrial IoT and computer vision system automating crop quality assessment directly on the production line
2. **The Power Farmer AI Computer Vision**: Models Specialized tools and libraries used to label and train the computer vision models on the Farmer Powzer QC Analyzer 
3. **The Farmer Power Platform**: A cloud platform that collects, analyzes quality data, and generates customized "Action Plans" and manages traceability across the value chain and creates an improvement loop back to the farmer

**IMPORTANT**: This document describes ONLY the **third component** of the Farmer Power Solution, the Farmer Power Platform. The two other parts are in separate projects. For more information about them:

* Farmer Power QC Analyzer: https://github.com/farmerpower-ai/farmer-power-qc-analyzer
* Power Farmer AI Computer Vision: https://github.com/farmerpower-ai/farmer-power-training


The first application of the system will be in Kenya to manage the quality improvement of the tea. 

## Executive summary 

The Farmer Power Platform is the third core component of the total Farmer Power solution, serving as the cloud service designed to collect, analyze quality data, and generate actionable insights to improve harvest quality

This platform is based on six interacting core models

| Models                | Goal                                                                                                                                               |
|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------|
| Collection Model      | Ingests quality grading results, loT sensor data, and external inputs (e.g.,Farmer Power QC Analyzer, weather services).                           |
| Knowledge Model       | Analyzes collected artifacts, enriches a vector database if required, and performs domain-specific inference (e.g., disease detection).            |
| Action Model          | Uses the knowledge base and a plantation's history to generate action plans and alerts for farmers.                                                |
| Plantation Model      | The digital twin of the farm, tracking historical data, performance, and improvements over time.                                                   |
| Market Analysis Model | Correlates factory quality data with buyer behavior and auction data to create "Market Preference Profiles· and enable intelligent lot allocation. |
| AI Model              | The fundation of the system, a fully configurable agentic workflow system, using LLM agents to support the other models                            |


These six models interact to each together, but they are independent of each other, there are clear contracts between them.

## Functional Requirements 

### The Plantation Model 

The plantation models must support the following data object: 

- Farm: where the harvest is collected contains static data about the farm, size, type of crops, geo-localization, but also all the history of the farm, quality result, analyze, action plan, etc.  
- Factory where the harvest of the farmer is processed and quality intake by the farmer power qc analyzer does the quality intake. 
- Grading models used by the QC Farmer Power Analyzer. 
- Buyer Profile: created by the Market Analysis Module 


 
#### Farm Data 

The farmer is where the harvest is collected contains static data about the farm, size, type of crops, geo-localization, but also all the history of the farm, quality result, analyze, action plan, etc.  

**Static Data**:

* Farm ID: A unique national ID for the farmer 
* Name of the Farmer 
* GPS Coordinates of the farm
* Altitude (given by GoogleAPI based on the GPS coordinate)
* Size of the plantation 
* County 
* Country 
* Crops (Tea, Coffee, etc.) 
* Reference of the Quality Grading model used by the Farmer Power QC Analyzer for this farm 
* Communication with the Farmer. (Language, SMS, etc.)

Managed via the Admin UI of the Platform. 

**Dynamic Data: Quality Intake**

Quality Intake Result of a crop bag collected by the Factory. 

* Collected timestamp 
* Bag ID, a unique ID of the Bag given by the QC Analyzer 
* Intake date and time 
* Intake duration in seconds
* Link to the Result of the Quality Intake in the document database. 
* Factory ID: ID of the factory where the quality intake took place. 

Collected by the `Collection Model `

**Dynamic Data: Poor Quality Analysis**

During the quality intake in the factory, the images of crop that do not match the minium quality standard are sent to the cloud platform with the associated grading result. The `knowledge model` will submit the image and result to the appropriate AI agent and store the analysis to the knowledge model. 

* Collected timestamp
* Bag ID of the quality intake
* Link to the quality result in the document database
* Link to the analysis in the knowledge database 

Collected by the `Collection Model`, analysis done by the knowledge model 

**Dynamic Data: Link to the daily weather report**

Every day the `Collection model` calls a weather API service for the region of each factory, the collected model validates and transforms this information in accurate information for the farm

* Date
* Link to the daily weather report in the document database 

**Dynamic Data: Actions plan generated by the system**

At regular interval the `Action Plan` model uses all the data of the farm to generate an action plan to implement in the farm to improve teh quality 

* Date
* Link to the action plan in the action plan database 

**Dynamic Data: Weekly Quality score of the factory**

A weekly quality score computed on the farmer weekly data

 
#### Factory Data 

Factory where the harvest of the farmer is processed and quality intake by the farmer power qc analyzer does the quality intake. 
 
** Static Data **

* Factory ID: A unique national ID for the Factory 
* Name of the Factory 
* GPS Coordinates of the factory 
* List of farmers who work with this factory, for each, the National ID of the Farmer, and the ID used by the factory 

#### Grading Model Data

The Grading Model Configuration of the Farmer Power Quality Analyzer is fully configurable and can be adapted to the needs of the different markets and crops.

The grading model is linked to a vision AI and is defined in the Power Farmer AI Computer Vision project. 

##### Grading type

The scoring can be done in different ways depending on the type of grading 

* **binary**: Accept to two possible values for the grade, for example, Accept/Reject 
* **ternary**: Accept to three possible values for the grade, for example, Premium/Standard/Reject
* **multi**: Accept to more than three possible values for the grade, for example, A,B,C,D

##### Attribute definitions

The `attributes` define the features used to evaluate the quality of the crop, for example:

```json 
{
  "attributes": {
    "moisture": {
      "num_classes": 3,
      "classes": ["excellent", "good", "bad"]
    },
    "branches": {
      "num_classes": 3,
      "classes": [1, 2, 3]
    },
    "color": {
      "num_classes": 3,
      "classes": ["excellent", "good", "poor"]
    }
  }
}
```

This is the attributes of the image classification model output.  In the model above, the model is a multi-head model, trained to classify three different attributes. 

In the following example, we have a mono head model, trained to classify one attribute.

```json 
{
  "attributes": {
    "quality": {
      "num_classes": 3,
      "classes": ["premium", "standard", "rejected"]
    }
  }
}
```

##### Grading Rules

The `grade_rules` define how a score is calculated for each attribute, for example:

````
 grade_rules={
        'scoring_map': {
            'moisture': {'excellent': 1.0, 'good': 0.6, 'bad': 0.2},
            'branches': {1: 1.0, 2: 0.6, 3: 0.2},
            'color': {'excellent': 1.0, 'good': 0.7, 'poor': 0.3}
        }
````

##### Attribute Weights

The `attribute_weights` defines the weight of each attribute in the overall score, for example:

```
attribute_weights={
            'moisture': 0.4,
            'branches': 0.35,
            'color': 0.25
        },
```

##### Grade Thresholds

The `grade_thresholds` defines the threshold for each grade, for example:

```
grade_thresholds={
            'premium': 0.85,
            'standard': 0.60
            'rejected': 0.0
        }
```

#### Buyer Profile data 

The platform uses an AI-driven Marketing Data Engine to analyze buyer behavior alongside real-time factory quality data, creating granular Market Preference Profiles that eliminate "blind" production. This intelligence model powers the Market-Quality Matching Engine, which performs Intelligent Lot Allocation by linking verified batches to their ideal 

Buyer profiles are created by the Market Analysis Model. 


### The AI Model 

The AI is the foundation of the system, It is a fully configured agentic workflow that uses LLM to provide analyses, integration, data validation, and event triggering for other models

It must support the following type of analysis: 

**Transform and Validate Data:** 

- From: Collection Model 
- Type of request: Validate and transform data 
- Goal: When the collection model receives new data, I can call the AI Model to validate and transform the data to a machine-readable format with its metadata like the farm and the factory Identification, the time stamp, etc. 
- Output: Data in a machine-readable data format (e.g. JSON, Image Binary, etc.) with its metadata (farmer identification, factory Identification, GPS Coordinate, timestamp, etc.) 

**Trigger and select an Analyse:** 

- From: KnowledgeModel, Action Model, Plantation Model, and Market Analysis Model 
- Type of Request: Find if an analysis needs to be done, extract data required by the analysis, and trigger it 
- Goal: Find the relevant analysis to execute depending on the data collected or analyzed by the other models. 
- Output: Trigger the right agent workflow, provide it the context and the required data 

**Analyze:**

- From: KnowledgeModel, Action Model, Plantation Model, and Market Analysis Model 
- Type of Request: LLM Analysis 
- Goal: Submit the request and the context to the right Agentic workflow 
- Output: a .MD document with the result of the request 

The agentic model must be fully configurable. It must be possible to define a new agent workflow by providing configuration data (without modifying the code or to redeploy the platform) like:

- The user prompt 
- LLM Model to use
- The system prompt 
- The data placeholder to be used in the prompt 
- The question(s) to ask the vector database to enrich the context
- Data extracted provided like other analyses, collected document like image, JSON document, etc.
- The agentic workflow pattern 
- Etc.

Agent Configuration must be versioned and all the modifications must be traceable. 


### The Collection Model 

Collect documents from various sources like, the final result of quality analyzer for a farmer at a factory, the image of crops that are not matching the minimum quality level, the weather in the region of a farm, etc.

The process is the following: 

1. The collected model checks on a source to find new data 
2. When It finds data in the source, it calls the AI Model to validate, extract, and transform the collected data
3. The transformed data is stored in the document database 
4. Based on the metadata extracted by the AI Model, the document is linked to the plantation model 


The collection model is fully configurable it must be possible to define a new source by configuration with: 

- The format of the data collected 
- The scheduling 
- The AI analysis to call to extract, format and validate the data and get the metadata required to link the collected data to the plantation model 
- The method to collect the data REST-API or STORAGE, to check if new files are present in a cloud storage account to get the result of quality analysis or event (Mail, WhatApps, Telegram) 


For example :

**collect quality from quality analyser**: 

- Source: collect quality data for tea leaves from Farmer power QC Analyzer 
- Scheduling: check for new files in a landing area every hour
- Collected document: a JSON document with the analysis result of the quality analysis a tea bag. 
- Analysis: Submit the collected data to the analysis defined in the source
- Integration: Based on the metadata provided by the validated quality result document (Farm ID, Factory ID, batch ID timestamp, Grading Model ID), stores it in the document database and link the document to the related plantation model entity (Farmer, Factory, Grading Model)

**Collect poor quality Image**:

- Source: collect image of tea leaves (with a result of the analysis for each image) that do not match the minimum quality standard from QC Analyzer 
- Scheduling: check for new files in a landing area every hour
- Collected document: image and quality result associated 
- Analysis: Submit the collected data to analysis defined in the source
- Integration: Based on the metadata provided by the validated quality (Farm ID, Factory ID, batch ID timestamp, Grading Model ID), stores image and associated quality result in the document database and link the document to the related plantation model entity (Farmer, Factory, Grading Model)

**Collect Current Weather**

- Source: call external weather service 
- Scheduling: Every day, call an external weather service to get the current weather condition for each farm
- Collected document: Reply from the weather service 
- Analysis: Submit the collected data to analysis defined in the source
- Integration: Receive pertinent information from the analysis and stores it the document database and links it to the farm in the plantation model 


### The Knowledge Model 

Analyses will be applied to the collected artifacts stored in the Analysis database and linked to plantation model 
Specific Knowledge for a specific agricultural industry (e.g. in Tea industry in Kenya) and stored in the Knowledge database (vector database)

The process is the following

1. When a document is collected or at regular interval, the AI Model executes a specific trigger analysis 
2. The AI Model queries select the right analysis to execute and query the required data, it can use the knowledge database if required to enrich the context  
3. The selected analysis is executed 
4. The analysis is stored in the analysis database and linked to the plantation model. 

Example of analysis: 

* Disease detection from images
* Irrigation problem 
* Agronomic issues
* Etc..


### The Action Plan model 

The action plan model uses the collected documents, the knowledge base, and the plantation's history to generate action plans to improve harvest quality on the farm. 
REMARK: As our primary target is the Agriculture Industry in Africa, the farmer is very often a basic person with a limited knowledge of English. So the action plan provided to the farmer must be simple and clear. We could envisage generating a detailed report for the Factory and a simple report for the farmer. 

* Generating alerts and action plans.
* Updating the plantation model based on knowledge base inputs.
* Interpret the knowledge base and plantation state.
* Generate alerts and weekly action plans.
* Update the plantation model with suggested actions.
* Configurable LLM-powered agent orchestration




### The Market Analysis Model

The platform uses an AI-driven Marketing Data Engine to analyze buyer behavior alongside real-time factory quality data, creating granular Market Preference Profiles that eliminate "blind" production. This intelligence model powers the Market-Quality Matching Engine, which performs Intelligent Lot Allocation by linking verified batches to their ideal buyer segments, ensuring premium pricing and significantly reducing unsold inventory through targeted pre-marketing.

The input of the Marketing model is the **Plantation Model** and the information queries in the external traceability platform (Starfish platform https://www.starfish-network.com/ ).

The target audience of these analyses is the Agricultural Regulatory Authorities

The process is the following:

1. At regular intervals the system selects and triggers a new LLm analysis. 
2. It queries in the plantation model and in the traceability platform to get the required data 
3. It run the LLM analysis 
4. It updates the buyer profiles in the plantation model 

Examples of analyses

* **Real-Time Data Capture (Marketing Data Engine):** The system first captures objective quality metrics for every batch at the factory level, including plucking standards, moisture content, leaf defects, and color/brightness indicators. This data creates a "digital quality passport" for every kilogram of tea.
* **Buyer Behavior Analysis:** The platform analyzes historical auction data to understand specific buyer habits, including their price tolerances, seasonal buying patterns, and specific reasons for rejecting lots.
* **Creation of Market Preference Profiles:** By combining factory quality data with buyer behavior, the AI generates granular profiles. For example, it defines the "United Kingdom Market" as demanding BP1 grades with a brightness score of 7.5+/10 and 60%+ fine leaf.
* **Intelligent Lot Allocation (Matchmaking):** The Market-Quality Matching Engine analyzes a newly produced batch (e.g., scored 8.2/10) against existing profiles and recommends the specific market segment that will pay a premium for that quality. 
* **Targeted Pre-Marketing:** Instead of selling "blindly," the Tea Board marketing team uses this data to upload quality proof to a Digital Showroom days before the auction, sending targeted reports directly to the identified buyers to drive confidence. 
* **Market Opportunity Scanning:** The Industry Advisory System continuously scans for gaps, such as predicting a "supply shortage of DUST1 in Pakistan" or a "surge in US organic demand," enabling the industry to pivot production strategies proactively. 
* **Continuous Feedback Loop:** The system improves over time by comparing its pre-auction price predictions with actual realized prices, refining its recommendations for the next cycle.


## Storage 

### The document database 

Contains the data collected by the Collection Model, can be JSON, Markdown, PDF, image, video
Each document is linked to the plantation model 
Can contain millions of documents 
Has a system to avoid storing the same document multiple times (e.g. hashcode on the content)
Has an indexation based on the type of collected source, the farmer, the factory, date range, content type,  etc..
Provide an API to allow searching and retrieving documents  

### The Analyse database 

Contains the analysis generated by in the Knowledge Model 
Each Analysis is linked to the plantation model 
Has an indexation based on the type of analysis, the farmer, the factory, date range,  etc..
Provide an API to allow searching and retrieving Analysis

### The knowledge Database 

A vector database that can be used by the AI Agent to enrich the context. Contains Architectural best practices for specific country and industry. 

### The Action Plan database

Contains the action plan generated by the Action Plan model 
Each Action plan is linked to a farm in the plantation model 
Has an indexation based on the farmer, the data range, etc..

### The Plantation Model Database 

Contains the Plantation Model 
Provides API To manage the data in the Plantation Model 

### The configuration Store 

Provide the configuration of collected sources, AI Model agent configuration, etc.

### Audit Store 

All the operations of the system must be traceable and stored  in an audit store 

## User Interface

### Admin User Interface

Target User: Administrator of the system at Farmepower.ai 
Operation: 
- Create and Update Farmer and Factory 
- Manage the subscription of the factory 
- Check the Audit store 

### Factory User Interface 

Target User: Provide a view on the Farmer Quality 
View:
- Global quality dashboard for the factory 
- Deep dive by farm 
- Top / Bottom quality provider 
- Follow the quality improvement of the farm 

### Agricultural Regulatory Authorities User Interface 

Agricultural regulatory bodies, which oversee food safety, standards, and fair trade in the agri-food sector. For example, in Kenya for the tea industry,  Tea Board of Kenya (TBK), established under the Tea Act 2020, which regulates production, promotion, standards, and trade. (https://www.teaboard.or.ke/)

View: 
- Global quality Dashboard
- Analysis done by the Market Analysis Model 


## Non Functional Requirements 

### Sizing 

For Kenya tea industry only  
- 100 Factories
- 800000 Farms
- Average of 200000 Bags Analyzed by day by factory 

### System Architecture & Interfaces

- Each Model must be deployed separately
- Each Model must offer a clear, well-documented 1interface 
- Communication via GRPC between models via sidecar 
- Backend for frontend to connect model to UI 
- Communication between the backend to frontend via REST-API and Web Sockets 
- Full observability (logging, metrics, alerts, tracing)
- Solid evolutive Architecture could be adapted easily to new crops, new market, etc..
- Fully configurable.
- Could change an AI Model by configuration without redeploying or restarting applications (Add a new analysis, tune the prompt, adapt the schema, change the AI agent workflow pattern, etc.)
- Add a new source to the collection model by configuration 
- Open Close Principle. 


### Technical landscape 

- Database: MongoDB and Azure Account storage for large documents
- Development language: Python 3.12
- Pydantic 2.0 
- AI Framework: LangChain and LangGraph, query Farmer Power Platform storage via MCP server 
- Separate deployment for each model 
- Run on Kubernetes (AKS)
- Connection between models via GRPC (via DAPR)  
- Observability: Open Telemetry via DAPR
- Vector database: Pinecone vector database - Knowledge model 
- Observability Platform: Grafana Cloud 
- Infrastructure backend abstraction via DAPR. (State Management, Secret Management, Publish-Subscribe, Jobs, Configuration, Service Invocation, etc..)
- Security: Oauth2 via JWT Token
- Backend for frontend API FastAPI and websocket 
- UI: React connection to backend via REST-API and Websocket






