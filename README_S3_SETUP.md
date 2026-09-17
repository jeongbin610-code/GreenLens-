# GreenLens S3 Policy RAG 적용본

이 폴더의 세 파일을 GitHub 저장소의 `GreenLens_app/`에 넣습니다.

```text
GreenLens_app/
├─ greenlens_core.py       # 기존 파일 교체
├─ requirements.txt        # 기존 파일 교체
└─ s3_policy_rag.py        # 새 파일 추가
```

## 연결 대상

기본값은 아래와 같이 코드에 설정되어 있습니다.

```text
버킷: est-7-policyrag
리전: ap-northeast-2
접두사: policy/index/current
임베딩: text-embedding-3-small
```

실행 시 아래 세 객체를 내려받습니다.

```text
s3://est-7-policyrag/policy/index/current/manifest.json
s3://est-7-policyrag/policy/index/current/index.faiss
s3://est-7-policyrag/policy/index/current/index.pkl
```

## 로컬 실행 전 환경변수

PowerShell 창에 실제 값을 직접 입력합니다. 값을 GitHub 파일에 넣지 마세요.

```powershell
$env:OPENAI_API_KEY="실제 OpenAI API 키"
$env:AWS_ACCESS_KEY_ID="실제 AWS Access Key ID"
$env:AWS_SECRET_ACCESS_KEY="실제 AWS Secret Access Key"
$env:AWS_DEFAULT_REGION="ap-northeast-2"
$env:GREENLENS_POLICY_BUCKET="est-7-policyrag"
$env:GREENLENS_POLICY_PREFIX="policy/index/current"
```

그다음 실행합니다.

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py --browser.gatherUsageStats false
```

정상 연결되면 콘솔에 다음과 비슷한 내용이 표시됩니다.

```text
S3 Policy RAG 로드: s3://est-7-policyrag/policy/index/current | vectors=275 | model=text-embedding-3-small
Policy RAG: 사용
```

## 선택 환경변수

기본값과 다르게 실행할 때만 설정합니다.

```text
GREENLENS_POLICY_EMBEDDING_MODEL=text-embedding-3-small
GREENLENS_POLICY_K=4
GREENLENS_POLICY_CACHE_DIR=로컬 캐시 폴더
```

## 필요한 S3 권한

앱의 AWS 자격 증명에는 최소한 다음 읽기 권한이 필요합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::est-7-policyrag/policy/index/current/*"
    }
  ]
}
```

## 중요

- `index.pkl`은 Python pickle 파일입니다. 이 코드는 사용자가 관리하는 지정 S3 버킷의 파일만 신뢰해 로드합니다. 해당 경로에 대한 쓰기 권한은 관리자에게만 제한하세요.
- `greenlens_core.py`는 `GreenLens_v8_Pipeline.ipynb`에서 자동 생성되는 파일입니다. `build_core.py`를 다시 실행하면 이번 변경이 사라집니다. 연결 확인 후에는 노트북의 `f9cf37d3` 셀에도 같은 변경을 반영해야 합니다.
- OpenAI API 키와 AWS 키를 GitHub에 커밋하지 마세요.
