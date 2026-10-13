if (!process.env.ARENA_E2E_API_PORT) throw new Error('Use npm run e2e');
module.exports = {'/api/**': {target:`http://127.0.0.1:${process.env.ARENA_E2E_API_PORT}`, secure:false, pathRewrite:{'^/api':''}}};
