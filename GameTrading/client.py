"""gridmap_client.py from
https://lovelace.oulu.fi/ohjelmoitava-web/ohjelmoitava-web/exercise-4-implementing-hypermedia-clients/
was used as a base for this client"""

"""tutorial from https://zetcode.com/python/rich/ was used for Rich formatting.
Prompt was not covered in tutorial so Rich documentation 
https://rich.readthedocs.io/en/stable/prompt.html 
provided additional information"""

import sys
import requests
from urllib.parse import urljoin
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

# Console for Rich
console = Console()


class GameTradeAPI:
    """
    Description:
    A client for interacting with the Game Trade API, handling authentication,
    user management and lists, game lists, and trading endpoints.
    """

    def __init__(self, host="http://86.50.168.120/"):
        """
        Description:
            Sets the host address and starts a requests session.
        Inputs:
            host (str): The base URL of the API. Defaults to "http://86.50.168.120/".
        Exceptions:
            AssertionError: Raised if the host string does not start with "http".
        """
        assert host.startswith("http"), "No protocol in host address"

        self.host = host
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        self.username = None

    # These two make the class compatible with with statements.
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.session.close()

    def set_auth(self, username, apikey):
        """
        Description:
            Sets session headers with provided API key and sets the active username.
        Inputs:
            username: The username to authenticate as.
            apikey: The API key associated with the user.
        """
        self.username = username
        self.session.headers.update({"GameTradeApi-Key": apikey})

    def delete_auth(self):
        """
        Description:
            Clears the current authentication credentials from the session headers.
        """
        self.username = None
        if "GameTradeApi-Key" in self.session.headers:
            del self.session.headers["GameTradeApi-Key"]

    def _handle_error(self, response):
        """
        Description:
            Parses and displays error messages based on HTTP response status codes.
        Inputs:
            response: Response object from the API.
        """
        try:
            error_data = response.json()
            error_message = error_data.get("message", "Unknown error")
            console.print(
                f"[bold red]Error ({response.status_code}):[/bold red] {error_message}"
            )
        except requests.exceptions.JSONDecodeError:
            if response.status_code == 404:
                console.print(
                    "[bold red]Error (404):[/bold red] The requested resource does not exist."
                )
            elif response.status_code == 403:
                console.print(
                    "[bold red]Error (403):[/bold red] You do not have permission to modify this resource."
                )
            elif response.status_code == 405:
                console.print("[bold red]Error (405):[/bold red] Method not allowed.")
            else:
                console.print(
                    f"[bold red]Error ({response.status_code}):[/bold red] An unexpected error occurred."
                )

    def _get(self, uri):
        """
        Description:
            Sends a GET request to the specified URI and returns the JSON.
        Inputs:
            uri: Endpoint path appended to the host.
        Outputs:
            Parsed JSON response if successful, otherwise None.
        """
        response = self.session.get(urljoin(self.host, uri))
        if response.status_code == 200:
            return response.json()
        self._handle_error(response)
        return None

    def _post(self, uri, data):
        """
        Description:
            Sends a POST request JSON to the specified URI.
        Inputs:
            uri: Endpoint path appended to the host.
            data: Data to be send in the request body.
        Outputs:
            The response object if successful (201), otherwise None.
        """
        response = self.session.post(urljoin(self.host, uri), json=data)
        if response.status_code == 201:
            return response
        self._handle_error(response)
        return None

    def _put(self, uri, data):
        """
        Description:
            Sends a PUT request JSON to the specified URI.
        Inputs:
            uri: Endpoint path appended to the host.
            data: Data to update the resource with.
        Outputs:
            True if the request was successful (204), False otherwise.
        """
        response = self.session.put(urljoin(self.host, uri), json=data)
        if response.status_code == 204:
            return True
        self._handle_error(response)
        return False

    def _delete(self, uri):
        """
        Description:
            Sends a DELETE request to the specified URI.
        Inputs:
            uri: Endpoint path appended to the host.
        Outputs:
            True if the deletion was successful (204), False otherwise.
        """
        response = self.session.delete(urljoin(self.host, uri))
        if response.status_code == 204:
            return True
        self._handle_error(response)
        return False

    def login(self, username, apikey):
        """
        Description:
            Attempts to log in a user. Sends empty JSON to the uri,
            checks if user path exists (is there a user named username),
            then if user is auhtenticated to add a game for the username.
            Uses status code to confirm if login was successful.
        Inputs:
            username: The user account name.
            apikey: The user's API key.
        """
        self.session.headers.update({"GameTradeApi-Key": apikey})

        uri = f"/api/users/{username}/games/"

        response = self.session.post(urljoin(self.host, uri), json={})

        if response.status_code == 404:
            console.print(
                f"[bold red]Login failed: User {username} does not exist.[/bold red]"
            )
            self.delete_auth()
            return

        if response.status_code == 403:
            console.print(
                f"[bold red]Login failed: Invalid API Key for user {username}.[/bold red]"
            )
            self.delete_auth()
            return

        if response.status_code in (400, 415):
            self.username = username
            console.print("[bold green]Logged in successfully![/bold green]")
            return

        console.print(
            f"[bold red]Unexpected error during login ({response.status_code}).[/bold red]"
        )
        self.delete_auth()
        return

    def get_all_users(self):
        """
        Description:
            Fetches all users from the API and displays them in a Rich table.
        """
        users = self._get("/api/users/")
        if users is not None:
            table = Table(
                title="Registered Users",
                header_style="bold magenta",
                border_style="cyan",
            )
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Username", style="magenta")
            table.add_column("Email", style="green")

            for user in users:
                table.add_row(
                    str(user.get("id")), user.get("username"), user.get("email")
                )
            console.print(table)

    def register(self, username, email, password):
        """
        Description:
            Registers a new user account with the provided details and automatically
            sets credenstials for the session with the newly generated API key.
        Inputs:
            username: The desired username.
            email: The user's email address.
            password: The desired password.
        """
        data = {"username": username, "email": email, "password": password}
        response = self._post("/api/users/", data)

        if response:
            console.print("[bold green]User created![/bold green]")
            key = response.json().get("apiKey")
            self.set_auth(username, key)
            console.print(
                f"[bold yellow]Your API Key: {key}[/bold yellow] (Saved to session)"
            )

    def get_user(self, username):
        """
        Description:
            Fetches and displays information about a specific user in a Rich panel.
        Inputs:
            username: The username of the user to check.
        """
        user = self._get(f"/api/users/{username}/")
        if user:
            console.print(
                Panel(
                    f"[bold]ID:[/bold] {user.get("id")}\n[bold]Username:[/bold] {user.get("username")}",
                    title=f"User Details: {username}",
                    border_style="cyan",
                )
            )

    def delete_user(self, username):
        """
        Description:
            Deletes a user's account and they are logged out.
        Inputs:
            username: The username of the account to be deleted.
        """
        if not self.username:
            console.print("[bold red]You must be logged in to delete user.[/bold red]")
            return

        if self._delete(f"/api/users/{username}/"):
            console.print(f"[bold green]User {username} deleted.[/bold green]")
            if username == self.username:
                self.delete_auth()
                console.print(
                    "[yellow]You are now logged out for all eternity *insert dramatic music*.[/yellow]"
                )

    def get_all_games(self):
        """
        Description:
            Retrieves all available games and displays them in a Rich table.
        """
        games = self._get("/api/games/")
        if games is not None:
            table = Table(
                title="Available Games",
                header_style="bold magenta",
                border_style="cyan",
            )
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Title", style="magenta")
            table.add_column("Owner", style="green")

            for game in games:
                table.add_row(str(game.get("id")), game.get("title"), game.get("owner"))
            console.print(table)

    def get_game_details(self, game_id):
        """
        Description:
            Fetches information about specific game ID and displays them in a Rich panel.
        Inputs:
            game_id: The ID of the game to be searched.
        """
        game = self._get(f"/api/games/{game_id}/")
        if game:
            details = (
                f"[bold magenta]Title:[/bold magenta] {game.get("title")}\n"
                f"[bold cyan]Description:[/bold cyan] {game.get("description")}\n"
                f"[bold cyan]Digital:[/bold cyan] {game.get("is_digital")}\n"
                f"[bold cyan]Traded:[/bold cyan] {game.get("is_traded")}\n"
                f"[bold cyan]Owner ID:[/bold cyan] {game.get("owner_id")}\n"
                f"[bold cyan]Image Path:[/bold cyan] {game.get("image_path")}"
            )
            console.print(
                Panel(
                    details,
                    title=f"Game Details (ID: {game.get("id")})",
                    border_style="magenta",
                )
            )

    def get_my_games(self):
        """
        Description:
            Fetches all games of the currently logged-in user and displays them
            in a Rich table.
        """
        if not self.username:
            console.print(
                "[bold red]You must be logged in to view your games.[/bold red]"
            )
            return

        games = self._get(f"/api/users/{self.username}/games/")
        if games is not None:
            table = Table(
                title=f"{self.username}'s Game Library",
                header_style="bold magenta",
                border_style="green",
            )
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Title", style="magenta")
            table.add_column("Owner", style="green")

            for game in games:
                table.add_row(str(game.get("id")), game.get("title"), game.get("owner"))
            console.print(table)

    def add_game(self, title, description, is_digital):
        """
        Description:
            Adds a new game to the logged-in user. It also attempts to fetch a
            thumbnail image for the game using the external CheapShark API.
        Inputs:
            title: Title of the game to be added.
            description: Description of the game.
            is_digital: True if the game is digital, False if it is physical.
        """
        if not self.username:
            console.print("[bold red]You must be logged in to add a game.[/bold red]")
            return

        thumb = ""
        data = None
        console.print("[italic cyan]Searching CheapShark image[/italic cyan]")
        try:
            # neat extra feature, get image from CheapShark API based on the game title
            # https://apidocs.cheapshark.com/ api docs for CheapShark
            response = requests.get(
                f"https://www.cheapshark.com/api/1.0/games?title={title}&limit=1",
                timeout=5,
            )
            if response:
                data = response.json()
            if data:
                thumb = data[0].get("thumb")
                console.print(f"[green]Found image[/green] {thumb}")
            else:
                console.print("[yellow]Could not fetch image from CheapShark.[/yellow]")
        except requests.RequestException:
            console.print("[yellow]Could not fetch image from CheapShark.[/yellow]")

        data = {
            "title": title,
            "description": description,
            "is_digital": is_digital,
            "image_path": thumb,
        }

        if self._post(f"/api/users/{self.username}/games/", data):
            console.print("[bold green]Game added![/bold green]")

    def delete_game(self, game_id):
        """
        Description:
            Removes a game from the logged-in user's game list based on the game ID.
        Inputs:
            game_id: ID of the game to be deleted.
        """
        if not self.username:
            console.print(
                "[bold red]You must be logged in to delete a game.[/bold red]"
            )
            return

        if self._delete(f"/api/users/{self.username}/games/{game_id}/"):
            console.print("[bold green]Game deleted![/bold green]")

    def get_all_trades(self):
        """
        Description:
            Retrieves all trade requests available and displays them in a Rich table.
        """
        trades = self._get("/api/trades/")
        if trades is not None:
            table = Table(
                title="All Trades", header_style="bold magenta", border_style="blue"
            )
            table.add_column("ID", style="cyan", justify="right")
            table.add_column("Status", style="magenta")
            table.add_column("Sender Game ID", style="blue", justify="right")
            table.add_column("Receiver Game ID", style="green", justify="right")

            for trade in trades:
                table.add_row(
                    str(trade.get("id")),
                    str(trade.get("status")),
                    str(trade.get("sender_game_id")),
                    str(trade.get("receiver_game_id")),
                )
            console.print(table)

    def get_trade_details(self, trade_id):
        """
        Description:
            Fetches the information of a trade and displays them in a Rich panel.
        Inputs:
            trade_id: ID of the trade request.
        """
        trade = self._get(f"/api/trades/{trade_id}/")
        if trade:
            details = (
                f"[bold cyan]Status:[/bold cyan] {trade.get("status")}\n"
                f"[bold cyan]Timestamp:[/bold cyan] {trade.get("timestamp")}\n"
                f"[bold cyan]Sender Game ID:[/bold cyan] {trade.get("sender_game_id")}\n"
                f"[bold cyan]Receiver Game ID:[/bold cyan] {trade.get("receiver_game_id")}"
            )
            console.print(
                Panel(
                    details,
                    title=f"Trade Details (ID: {trade.get("id")})",
                    border_style="blue",
                )
            )

    def create_trade(self, sender_game_id, receiver_game_id):
        """
        Description:
            Creates a new trade request, proposing a trade of the logged-in user's game
            for another user's target game.
        Inputs:
            sender_game_id: The ID of the game the user is offering.
            receiver_game_id: The ID of the game the user is requesting.
        Exceptions:
            ValueError: If either sender_game_id or receiver_game_id cannot be set to an integer.
        """
        if not self.username:
            console.print(
                "[bold red]You must be logged in to create a trade request.[/bold red]"
            )
            return

        data = {
            "sender_game_id": int(sender_game_id),
            "receiver_game_id": int(receiver_game_id),
        }

        if self._post(f"/api/users/{self.username}/trades/", data):
            console.print("[bold green]Trade request created![/bold green]")

    def update_trade_status(self, trade_id, status):
        """
        Description:
            Updates the status of an existing trade request (Accept or Decline).
        Inputs:
            trade_id: ID of the trade request.
            status: Status string to apply to the trade.
        """
        if not self.username:
            console.print(
                "[bold red]You must be logged in to manage trades.[/bold red]"
            )
            return

        data = {"status": status}
        if self._put(f"/api/users/{self.username}/trades/{trade_id}/", data):
            console.print("[bold green]Trade status updated![/bold green]")

    def get_trade_success_count(self):
        """
        Description:
            Retrieves information about the number of successful and total trades and
            displays them in a Rich panel.
        """
        data = self._get("/api/trades/successful-count/")
        if data:
            console.print(
                Panel(
                    f"[bold green]Successful Trades:[/bold green] {data.get("successful_trades", "N/A")}\n"
                    f"[bold cyan]Total Trades:[/bold cyan] {data.get("total_trades","N/A")}",
                    title="Trade Analytics",
                    border_style="yellow",
                )
            )


def main():
    """
    Description:
        The main loop for the CLI application. Lists option and interprets inputs to
        the appropriate GameTradeAPI methods.
    """
    console.print(
        Panel.fit(
            "[bold blue]Game Trading CLI[/bold blue]",
            border_style="blue",
        )
    )

    with GameTradeAPI("http://86.50.168.120/api/") as api:
        while True:
            console.print("\n[bold underline]Main Menu:[/bold underline]\n")
            console.print("[cyan]1.[/cyan] Register Account")
            console.print("[cyan]2.[/cyan] Login")
            console.print("[cyan]3.[/cyan] View All Available Games")
            console.print("[cyan]4.[/cyan] View My Games")
            console.print("[cyan]5.[/cyan] Add Game")
            console.print("[cyan]6.[/cyan] Delete Game")
            console.print("[cyan]7.[/cyan] Create Trade Request")
            console.print("[cyan]8.[/cyan] Handle Trade Request")
            console.print("[cyan]9.[/cyan] View All Users")
            console.print("[cyan]10.[/cyan] View User Details")
            console.print("[cyan]11.[/cyan] View Trade Details")
            console.print("[cyan]12.[/cyan] View Game Details")
            console.print("[cyan]13.[/cyan] View All Trades")
            console.print("[cyan]14.[/cyan] View Trade Analytics")
            console.print("[cyan]15.[/cyan] Delete User")
            console.print("[cyan]16.[/cyan] Exit")

            option = Prompt.ask("\nSelect an option", default=1)

            if option == "1":
                username = Prompt.ask("Username")
                email = Prompt.ask("Email")
                password = Prompt.ask("Password", password=True)
                api.register(username, email, password)

            elif option == "2":
                username = Prompt.ask("Enter your registered username")
                apikey = Prompt.ask("Enter your API Key")
                api.login(username, apikey)

            elif option == "3":
                api.get_all_games()

            elif option == "4":
                api.get_my_games()

            elif option == "5":
                title = Prompt.ask("Game Title")
                description = Prompt.ask("Game Description")
                is_digital = Confirm.ask("Is it digital?")
                api.add_game(title, description, is_digital)

            elif option == "6":
                game_id = Prompt.ask("Enter the ID of the game to delete")
                try:
                    api.delete_game(int(game_id))
                except ValueError:
                    console.print(
                        "[bold red]Invalid input. Game IDs must be integer.[/bold red]"
                    )

            elif option == "7":
                sender_game_id = Prompt.ask("Enter ID of YOUR game you want to trade")
                receiver_game_id = Prompt.ask("Enter ID of TARGET game you want")
                try:
                    api.create_trade(int(sender_game_id), int(receiver_game_id))
                except ValueError:
                    console.print(
                        "[bold red]Invalid input. Game IDs must be integer.[/bold red]"
                    )

            elif option == "8":
                trade_id = Prompt.ask("Enter Trade ID")
                status = Prompt.ask(
                    "Enter new status",
                    choices=["Accepted", "Declined"],
                    default="Accepted",
                )
                api.update_trade_status(trade_id, status)

            elif option == "9":
                api.get_all_users()

            elif option == "10":
                username = Prompt.ask("Enter the username to view")
                api.get_user(username)

            elif option == "11":
                trade_id = Prompt.ask("Enter Trade ID to view details")
                api.get_trade_details(trade_id)

            elif option == "12":
                game_id = Prompt.ask("Enter Game ID to view details")
                api.get_game_details(game_id)

            elif option == "13":
                api.get_all_trades()

            elif option == "14":
                api.get_trade_success_count()

            elif option == "15":
                username = Prompt.ask("Enter the username to delete")
                api.delete_user(username)

            elif option == "16":
                console.print("[bold green]Bye Bye![/bold green]")
                sys.exit(0)


if __name__ == "__main__":
    main()
