## LINE BotでAWS暗記カードを作る

#### はじめに

- LINE Botで暗記カードを作ったときのスクリプトなど一式です。
- LINE Botと自作APIを組み合わせます。
- ここは自作APIを作るために必要な情報を置いています。
- ここで作る自作APIは、クラウドサービス AWS の`API Gateway`, `Lambda`, `DynamoDB` を使用します。
- また、画像の外部公開に `S3` を使用します。

#### デモ動画

[![Audi R8](http://img.youtube.com/vi/dRjSgsZwZDg/0.jpg)](https://www.youtube.com/watch?v=dRjSgsZwZDg "LineBot AWS FlashCard")

#### ファイルの説明

|ファイル|概要|
|---|---|
|lambda_function.py|AWS LambdaのPython 3.6スクリプト|
|data.json|DynamoDBに登録するデータ|
|putdata.py|data.jsonをDynamoDBに登録するPython3スクリプト|
|imgsディレクトリ|画像データ群|

#### 作り方

(1) [こちらの記事](https://qiita.com/suo-takefumi/items/65128ba82081b8fc6b51)を参考に、オウム返しするLINE Botを作ります。
(2-1) DynamoDBに2つテーブルを作成します。

- テーブル名 `questions`
  - プライマリパーティションキー `category`
  - プライマリソートキー `by_at`
- テーブル名 `results`
  - プライマリパーティションキー `userid`
  - プライマリソートキー `end_date`

(2-2) `questions`テーブルにデータを登録します。

- 手順(1)で作成した`questions`テーブルに`data.json`の情報を`putdata.py`スクリプトでDynamoDBに登録します。
- 実行コマンドは以下です。

```
$ python putdata.py data.json
```

`questions`テーブルにデータが登録されれば成功です。

(3) S3で画像をインターネット公開します。

- S3バケットを作成し、imgs配下の画像をインターネット公開します。
- 以下のようなURLでS3バケットに登録した画像が表示できれば成功です。
  - https://{S3バケット名}.s3-ap-northeast-1.amazonaws.com/xxxx.png

(4) Lambdaスクリプトを更新します。

- 手順(1)で作成したオウム返しLINE BotのLambdaスクリプトを`Lambda_function.py`に上書きします。
- また、環境変数 `S3PATH` を追加し、手順(3)のS3バケット名を値として設定します。

手順(4)の後、LINE BotでAWS暗記カードが動くと成功です。
