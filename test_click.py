import click

@click.command()
@click.argument('nome')
def main(nome):
    print("Olá,", nome)

if __name__ == "__main__":
    main()