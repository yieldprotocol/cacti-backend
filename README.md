<div align="center">
  <h1 align="center">🌵🌵🌵 Cacti 🌵🌵🌵 </h1>
  <h2 align="center"> <b>Cacti Backend</b> - <a href="https://github.com/yieldprotocol/cacti-frontend">Cacti Frontend</a></h2>
  <p align="center">
    Natural language interactions with web3.
    <br />
    <br />
    <a href="https://twitter.com/yield">Twitter</a>
    ·
    <a href="https://discord.gg/JAFfDj5">Discord</a>
    ·
    <a href="https://github.com/yieldprotocol/cacti-backend/issues">Report a Bug</a>
  </p>
</div>

<br />

![A screenshot of Cacti.](/screenshot.jpg)

## About

Cacti is a natural language interface for interacting with web3. It uses OpenAI function calling capability and a small but growing library of web3 interactions (called "widget commands") to enable chat based interactions.  

Cacti includes a frontend and backend repo. This is the backend. The frontend is [here](https://github.com/yieldprotocol/cacti-frontend).

The Cacti backend manages chat interactions with OpenAI, chat history, and user logins. 

### Features

**Widget Commands**: Central to Cacti's extensible design are the Widget Commands. These commands act as functions that an LLM can call to display an interaction dialogue box, allowing users to engage in web3 actions or access data seamlessly. The Widget Commands can be expanded upon, allowing for a broad array of functions catered to the user's needs.

**Eval**: Cacti employs a flexible evaluation framework that is crucial for developers wishing to assess the performance of added widgets. This includes features like hard-coded testing, automatic evaluations, and evaluations via manually annotated test samples that can be input via a CSV file. 

**Chat Context**: All dialog boxes can add information to the chat context, enabling the LLM use context added by previous widget commands to execute a later command effectively, enhancing the overall user experience.

**Configurable Chat Modules**: Chat modules can be configured to permit the use of alternative LLMs, fine-tuned LLMs, alternate prompts to LLMs, etc. Different chat modules can be used just by using a modified URL. This allows for easy testing of potential improvements to the chat modes and new features. 

**Streaming Support**: Cacti supports streaming from LLM models, providing users with real-time updates. The system can sensibly handle widget commands included in the LLM stream, ensuring smooth and intuitive interactions.

**Support for Structured/Rich Media Output**: Cacti offers the ability to handle widget commands that need to display structured or rich media output as part of the interface. This includes tables, NFTs, and other forms of rich media, allowing users to engage with a dynamic and visually engaging interface.

**Cacti ReactJS Component Framework**: For easy UI integration, Cacti has built a ReactJS component framework that requires only basic ReactJS, HTML, and CSS skills. The components are composable, making it possible to mix and match the components to fit the information display requirements of the widget. Widget commands can be built on the frontend, or invoked from the backend using string responses. Developers can create more sophisticated functions by creating separate React components if needed.

**Wallet-based Authentication**: Cacti uses wallet-based authentication specifically for web3 wallets like MetaMask. This provides a secure means of identification and ensures the secure execution of web3 transactions.

**Transaction Handling**: Cacti is designed to handle web3 transactions on Ethereum or Layer 2 solutions (L2s). It abstracts away the complexity of transaction handling from the integrator. All the integrator needs to do is pass the transaction details, and Cacti takes care of the rest, ensuring a user-friendly experience for those engaging with web3 protocols.

## Running Locally

To develop locally, you need to run the frontend and backend, because
the dev and production deployments do not allow local URLs to interact
with them.

## Usage Guide
The usage guide for the Cacti chatbot is available [here](./usage_guide.md)

## To run the backend locally:
* Install [Docker](https://docs.docker.com/get-docker/)
* Requires Python 3.10 (DO NOT use higher versions as 'pysha3' dependency has issues with them)
* Run the docker containers - `docker compose -f ./docker/docker-compose.yml up -d`
* Run `docker ps` and check the status on both Postgres DB and Weaviate Vector DB to make sure they are running
* Copy and setup `.env` file in `./env` dir - `cp ./env/.env.example ./env/.env`
* Set your own credentials for the services defined in the `./env/.env` file
* Setup Python virtualenv - `python3 -m venv ../venv`
* Activate virtualenv - `source ../venv/bin/activate`
* Install dependencies - `pip install -r requirements.txt`
* Populate vector index with widgets - `python -m scripts.check_update_widget_index`
* Populate vector index with app info - `python -c "from index import app_info; app_info.backfill()"`
* Run DB migrations - `./db_schema_sync.sh`
* Run server - `./start.sh`

## To add a new env var/secret:
* Update `./env/.env.example` and `./env/.env` files
* Update `cloudbuild.yaml` file for GCP deployment

## Steps to add new widget command
- Update `widgets.yaml` with the widget command details
    - If no value has to be returned please specify an empty string '' for `return_value_description`
- Increment the numeric version in `WIDGET_INDEX_NAME` constant in `utils/constants.py`
- For local env, the widget index name would use your OS login name to create an isolated index. For dev/prod, the widget index would be the numeric version mentioned above. (more info in `scripts/check_update_widget_index.py`)
- Run this Python command to update your widget index with the new widget `python -m scripts.check_update_widget_index`
- Ensure textual translation for the display widget command is added to the `_widgetize_inner` function in `display_widget.py` file

## Contributing

See the [open issues](https://github.com/yieldprotocol/cacti-backend/issues) for a list of proposed features (and known issues).

