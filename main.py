import discord
import importlib.util
import pathlib
import os


def parser(message, activation="!", separator=" ", letter_argument="-", word_argument="--"):
    if not message[0] == activation:
        return None

    message.replace('\r', ' ').replace('\n', ' ')

    command, *elements = message.split(separator)
    arguments = {}
    key = ""
    values = []

    for element in elements:
        element.strip()

        if element[0:2] == word_argument:
            if values:
                arguments.update({key: values})
            key = element.strip(word_argument)
            values = []

        elif element[0] == letter_argument:
            if values:
                arguments.update({key: values})
            for x in element.strip(letter_argument)[:-1]:
                arguments.update({x: []})
            key = element.strip(letter_argument)[-1]
            values = []

        else:
            values.append(element)

    arguments.update({key: values})

    return command.strip(activation), arguments


client = discord.Client()


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


@client.event
async def on_message(message):
    if message.author == client.user:  # It is our own message
        return

    ret = parser(message.content)
    if ret is not None:
        command, arguments = ret
        for mod in modules:
            for func in dir(mod):
                if func == command:
                    command_function = getattr(mod, func)
                    if callable(command_function):
                        await command_function(arguments, message)


# Look in the commands directory and import everything from there
modules = []
for pyfile in pathlib.Path("commands").glob('*.py'): # or perhaps 'script*.py'
    spec = importlib.util.spec_from_file_location(f"{__name__}.imported_{pyfile.stem}" , pyfile)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    modules.append(module)

client.run(os.getenv("TOKEN"))
