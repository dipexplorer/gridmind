const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

async function run() {
  const email = `test${Date.now()}@example.com`;
  const password = "Password123!";
  
  const { data, error } = await supabase.auth.signUp({
    email,
    password
  });
  
  if (error) {
    console.error("SignUp error:", error);
    return;
  }
  
  console.log("Token:", data.session?.access_token);
  if (data.session?.access_token) {
    const tokenParts = data.session.access_token.split('.');
    const header = JSON.parse(Buffer.from(tokenParts[0], 'base64').toString());
    console.log("Header:", header);
  }
}

run();
