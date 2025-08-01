from dotenv import load_dotenv, set_key
from flask import Flask, request
import requests
import os
import webbrowser


class FirstAuth:
    def __init__(self, env:str = "../data/.env"):
        self.__env__ = env
        load_dotenv(self.__env__)
        self.__client_id__ = os.getenv('CLIENT_ID')
        self.__client_secret__ = os.getenv('CLIENT_SECRET')

        self.__code_challenge__ = os.getenv('CODE_CHALLENGE')
        self.__code_verifier__ = os.getenv('CODE_VERIFIER')

        self.__scopes__ = os.getenv('SCOPES')
        self.__redirect_url__ = os.getenv('REDIRECT_URL')


    def auth_browser(self):
        self.__show_sign_in_page__()
        self.__run__()


    def __show_sign_in_page__(self):
        print("Open this link in browser:")
        url = f'https://auth.dodois.com/connect/authorize?client_id={self.__client_id__}&scope={self.__scopes__}&response_type=code&redirect_uri={self.__redirect_url__}&code_challenge={self.__code_challenge__}&code_challenge_method=S256'
        print(url)
        webbrowser.open(url)

    def __run__(self):
        app = Flask(__name__)

        @app.route("/")
        def get_token():
            args = request.args
            code = args.get("code", default="", type=str)

            request_body = {
                "client_id": self.__client_id__,
                "client_secret": self.__client_secret__,
                "code_verifier": self.__code_verifier__,
                "scope": self.__scopes__,
                "grant_type": "authorization_code",
                "redirect_uri": self.__redirect_url__,
                "code": code
            }
            auth_result = requests.post("https://auth.dodois.com/connect/token", data=request_body)

            if auth_result.status_code == 200:
                print(auth_result.json())
                refresh_token = auth_result.json().get("refresh_token")
                if refresh_token:
                    set_key(self.__env__, "REFRESH_TOKEN", refresh_token)
                    return 'Success', 200
                else:
                    print("No refresh token received")
                    return 'Error: No refresh token received', 400
            else:
                print("Failed to get token:", auth_result.json(),auth_result.status_code)
                return 'Error: Failed to get token', 500


        app.run(host="localhost", port=5001, ssl_context='adhoc')

if __name__ == '__main__':
    auth = FirstAuth()
    auth.auth_browser()