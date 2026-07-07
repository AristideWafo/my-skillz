# .github/workflows/ansible-ci.yml
name: Ansible CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  ANSIBLE_FORCE_COLOR: "1"
  PY_COLORS: "1"

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install dependencies
        run: |
          pip install ansible ansible-lint yamllint
          ansible-galaxy collection install -r requirements.yml

      - name: Run yamllint
        run: yamllint -c .yamllint.yml .

      - name: Run ansible-lint
        run: ansible-lint --profile production

  molecule:
    name: Molecule — ${{ matrix.role }}
    runs-on: ubuntu-latest
    needs: lint
    strategy:
      matrix:
        role:
          - nginx
          - postgresql
          - base-os
          - monitoring-agent
      fail-fast: false    # Continuer les tests des autres rôles si un échoue
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip

      - name: Install Molecule
        run: pip install molecule molecule-docker ansible docker

      - name: Run Molecule tests
        working-directory: roles/${{ matrix.role }}
        run: molecule test

  check-staging:
    name: Dry-run (Staging)
    needs: molecule
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials (OIDC — pas de clés statiques)
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/ansible-runner-staging
          aws-region: eu-west-1

      - name: Get vault password from SSM
        run: |
          aws ssm get-parameter \
            --name "/ansible/vault-pass/staging" \
            --with-decryption \
            --query "Parameter.Value" \
            --output text > /tmp/vault-pass-staging
          chmod 400 /tmp/vault-pass-staging

      - name: Ansible dry-run on staging
        run: |
          ansible-playbook site.yml \
            -i inventories/staging/ \
            --check \
            --diff \
            --vault-password-file /tmp/vault-pass-staging

      - name: Cleanup vault password file
        if: always()
        run: rm -f /tmp/vault-pass-staging

  deploy-staging:
    name: Deploy to Staging
    needs: check-staging
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/ansible-runner-staging
          aws-region: eu-west-1

      - name: Deploy to staging
        run: |
          ansible-playbook site.yml \
            -i inventories/staging/ \
            --vault-password-file <(aws ssm get-parameter --name "/ansible/vault-pass/staging" --with-decryption --query "Parameter.Value" --output text)

  deploy-production:
    name: Deploy to Production
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production    # Requiert approbation manuelle dans GitHub Environments
    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::${{ vars.AWS_ACCOUNT_ID }}:role/ansible-runner-prod
          aws-region: eu-west-1

      - name: Deploy to production (rolling 10%)
        run: |
          ansible-playbook site.yml \
            -i inventories/production/ \
            --vault-password-file <(aws ssm get-parameter --name "/ansible/vault-pass/prod" --with-decryption --query "Parameter.Value" --output text)