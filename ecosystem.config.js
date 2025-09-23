module.exports = {
    apps: [{
      name: 'verifit-backend',
      script: 'run.py',
      interpreter: '/mnt/hdd_sda/.conda/envs/verifit/bin/python',
      cwd: '/home/nikmir419/VeriFit-Backend',
      env_file: '.env',
      env: {
        NODE_ENV: 'production',
        DATABASE_URL: 'postgresql://verifit_master:verifit123@verifit-db.cpk0oamsu0g6.us-west-1.rds.amazonaws.com:5432/verifit_db',
        API_BASE_URL: 'http://14.39.95.228:8000',
        CORS_ORIGINS: '["http://localhost:3000", "http://localhost:3001", "http://localhost:8000", "http://localhost:8001", "http://192.168.0.21:3001", "http://192.168.0.21:3000", "http://14.39.95.228:3001", "http://14.39.95.228:3000"]',
        PORT: 8001,
        LAMBDA_FUNCTION_URL: 'https://fm32g7knrrbb226tl63rok63j40vupaa.lambda-url.us-west-1.on.aws/',
        LAMBDA_FUNCTION_URL_AUTH: 'NONE',
        LAMBDA_QUESTIONS_FUNCTION_NAME: 'verifit-generate-questions',
        LAMBDA_QUESTIONS_FUNCTION_URL: 'https://tobz2wdtm5iightngdg4fmkggq0cohmp.lambda-url.us-west-1.on.aws/',
        LAMBDA_KB_INGEST_FUNCTION_URL: 'https://m32daztjervwoogwvkqssdvqny0fruzi.lambda-url.us-west-1.on.aws/',
        LAMBDA_EVALUATION_FUNCTION_URL: 'https://h7g4uvtvqdnzh3oze6yluke53e0ppiwd.lambda-url.us-west-1.on.aws/'
      },
      instances: 1,
      exec_mode: 'fork',
      watch: false,
      max_memory_restart: '1G',
      error_file: './logs/err.log',
      out_file: './logs/out.log',
      log_file: './logs/combined.log',
      time: true,
      restart_delay: 4000,
      max_restarts: 10,
      min_uptime: '10s',
      kill_timeout: 5000,
      listen_timeout: 3000,
      shutdown_with_message: true
    }]
  };
  