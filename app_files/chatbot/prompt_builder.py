import logging
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

def build_question_prompt(system_prompt_template: str, brd_questions: str) -> ChatPromptTemplate:
    """
    Creates the ChatPromptTemplate for the chatbot.
    """
    question_prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt_template + "\n\nBRD QA : {brd_questions}"),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ])
    logging.info("Question prompt template created.")
    return question_prompt