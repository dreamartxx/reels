<?php
declare(strict_types=1);
require_once __DIR__.'/download_names.php';
ini_set('display_errors','0');
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');
function reply(mixed $data,int $code=200): never {http_response_code($code);echo json_encode($data,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);exit;}
function fail(string $s,int $code=400): never {reply(['detail'=>$s],$code);}
function body(): array {static $data; if($data===null){$raw=file_get_contents('php://input');if(strlen($raw)>1500000)fail('İstek çok büyük.',413);$data=json_decode($raw,true);if(!is_array($data))fail('Geçersiz JSON.');}return $data;}
function enc(mixed $v): string{return json_encode($v,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR);}
function uid(): string{return bin2hex(random_bytes(16));}
$configPath=getenv('REELS_CONFIG')?:dirname(__DIR__,2).'/reels-private/config.php';
if(!is_file($configPath))fail('Site yapılandırması henüz tamamlanmadı.',503);
$config=require $configPath;
$db=null;
for($attempt=0;$attempt<3;$attempt++){
 try{$db=new PDO($config['dsn'],$config['db_user']??null,$config['db_password']??null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,PDO::ATTR_TIMEOUT=>5]);break;}
 catch(Throwable $e){if($attempt<2)usleep(150000*($attempt+1));else error_log('Reels DB connection failed: '.$e->getCode());}
}
if(!$db)fail('Veritabanına bağlanılamadı.',503);
$storage=$config['storage'];if(!is_dir($storage))mkdir($storage,0700,true);
if(!is_file($storage.'/schema-v1')){
 try{$db->exec(file_get_contents(dirname($configPath).'/schema.sql'));file_put_contents($storage.'/schema-v1','1');}
 catch(Throwable $e){error_log('Reels schema: '.$e->getMessage());fail('Veritabanı tabloları kurulamadı.',503);}
}
function q(string $sql,array $args=[]): PDOStatement{global $db;$s=$db->prepare($sql);$s->execute($args);return $s;}
function meta(string $name,?string $value=null): ?string{
 if($value===null){$r=q('SELECT value FROM reels_meta WHERE name=?',[$name])->fetch();return $r?$r['value']:null;}
 q('REPLACE INTO reels_meta(name,value) VALUES(?,?)',[$name,$value]);return $value;
}
function project(string $id): array{if(!preg_match('/^[a-f0-9]{32}$/D',$id))fail('Proje bulunamadı.',404);$r=q('SELECT document FROM reels_projects WHERE id=?',[$id])->fetch();if(!$r)fail('Proje bulunamadı.',404);return json_decode($r['document'],true);}
function saveProject(array $p): array{$p['updated_at']=time();q('UPDATE reels_projects SET document=?,updated_at=? WHERE id=?',[enc($p),time(),$p['id']]);return $p;}
function dirFor(string $id): string{global $storage;return $storage.'/'.$id;}
function jobRecord(array $r): array{return ['id'=>$r['id'],'project_id'=>$r['project_id'],'kind'=>$r['kind'],'status'=>$r['status'],'progress'=>(float)$r['progress'],'message'=>$r['message'],'cancel'=>(bool)$r['cancelled'],'result'=>$r['result']?json_decode($r['result'],true):null];}
function getJob(string $id): array{$r=q('SELECT * FROM reels_jobs WHERE id=?',[$id])->fetch();if(!$r)fail('İşlem bulunamadı.',404);return $r;}
function enqueue(string $pid,string $kind,array $payload): array{
 global $db;
 // Serialize queue changes through the project row to prevent double-click races.
 $db->beginTransaction();q('UPDATE reels_projects SET updated_at=updated_at WHERE id=?',[$pid]);
 $active=q("SELECT id FROM reels_jobs WHERE project_id=? AND status IN ('queued','running') AND kind<>'scene'",[$pid])->fetch();
 if($active&&$kind!=='scene'){$db->rollBack();fail('Bu projede devam eden işlem var.',409);}
 if($kind==='scene')q("UPDATE reels_jobs SET status='cancelled',cancelled=1 WHERE project_id=? AND kind='scene' AND status='queued'",[$pid]);
 $count=(int)q("SELECT COUNT(*) FROM reels_jobs WHERE status IN ('queued','running')")->fetchColumn();
 if($count>=8){$db->rollBack();fail('İşlem sırası dolu; devam eden işlemi bekleyin.',429);}
 $id=uid();q("INSERT INTO reels_jobs(id,project_id,kind,status,payload,message,created_at) VALUES(?,?,?,'queued',?,?,?)",[$id,$pid,$kind,enc($payload),'Video motoru bekleniyor…',time()]);$db->commit();return jobRecord(getJob($id));
}
function clean(string $s): string{return trim(preg_replace('/\[[^\]]*\]/u','',$s));}
function splitText(string $s,string $mode): array{
 $s=clean($s);$parts=[];
 if($mode==='lines')$parts=preg_split('/\R/u',$s);
 else foreach(preg_split('/\n\s*\n/u',$s) as $stanza){$stanza=trim(preg_replace('/\s+/u',' ',$stanza));array_push($parts,...preg_split('/(?<=[.!?…])\s+/u',$stanza));}
 $parts=array_values(array_filter(array_map('trim',$parts),fn($x)=>$x!==''));
 if(!$parts||count($parts)>180)fail('1–180 cümle girin.',422);
 foreach($parts as $p)if(mb_strlen($p)>1200)fail('Çok uzun cümleyi bölün.',422);
 return $parts;
}
function validateEdit(array $e,array $p,bool $needSentences=false): array{
 if(!isset($e['name'],$e['text'],$e['style'],$e['sentences'])||!is_string($e['name'])||mb_strlen(trim($e['name']))<1||mb_strlen($e['name'])>120||!is_string($e['text'])||mb_strlen($e['text'])>24000||!is_array($e['sentences'])||count($e['sentences'])>180)fail('Geçersiz proje alanları.',422);
 if($needSentences&&!count($e['sentences']))fail('Önce şiiri hizalayın.',422);
 $prev=0;$ids=[];
 foreach($e['sentences'] as &$s){
  if(!is_array($s)||!isset($s['id'],$s['text'],$s['start'],$s['end'])||!is_string($s['text'])||!is_numeric($s['start'])||!is_numeric($s['end']))fail('Geçersiz cümle.',422);
  $s['text']=clean($s['text']);$start=(float)$s['start'];$end=(float)$s['end'];
  if(!$s['text']||mb_strlen($s['text'])>1200||isset($ids[$s['id']])||!is_finite($start)||!is_finite($end)||$start<0||$start<$prev-.001||$end-$start<.03||$end>$p['audio']['duration']+.001)fail('Cümleler sıralı, ses süresi içinde ve çakışmasız olmalı.',422);
  $ids[$s['id']]=1;$prev=$end;
 }
 unset($s);
 $style=$e['style'];
 if(!in_array($style['font']??'', ['serif','sans','mono'],true)||!in_array($style['template']??'', ['dark','gold','paper','typewriter'],true))fail('Geçersiz tasarım.',422);
 foreach(['background','foreground','accent'] as $key)if(!preg_match('/^#[a-f0-9]{6}$/iD',$style[$key]??''))fail('Geçersiz renk.',422);
 foreach(['font_size'=>[30,130],'line_height'=>[1,1.7],'transition'=>[.2,1.2],'position'=>[-.15,.15],'safe_top'=>[80,400],'safe_bottom'=>[100,500],'safe_left'=>[50,220],'safe_right'=>[50,260],'grain'=>[0,.08]] as $k=>$bounds){$v=$style[$k]??null;if(!is_numeric($v)||$v<$bounds[0]||$v>$bounds[1])fail('Geçersiz tasarım değeri: '.$k,422);}
 return array_intersect_key($e,array_flip(['name','text','style','sentences']));
}
function fileResponse(string $path,string $type,?string $download=null): never{
 if(!is_file($path))fail('Dosya bulunamadı.',404);
 if(session_status()===PHP_SESSION_ACTIVE)session_write_close();
 global $db;$db=null; // Release the connection before streaming media.
 header('Content-Type: '.$type);header('Accept-Ranges: bytes');
 if($download)header('Content-Disposition: attachment; filename="'.$download.'"');
 $size=filesize($path);$start=0;$end=$size-1;
 if(isset($_SERVER['HTTP_RANGE'])){
  if(!preg_match('/^bytes=(\d*)-(\d*)$/D',$_SERVER['HTTP_RANGE'],$m))fail('Geçersiz byte aralığı.',416);
  if($m[1]===''){$start=max(0,$size-(int)$m[2]);}else{$start=(int)$m[1];$end=$m[2]===''?$end:min($end,(int)$m[2]);}
  if($start>$end||$start>=$size){header("Content-Range: bytes */$size");http_response_code(416);exit;}
  http_response_code(206);header("Content-Range: bytes $start-$end/$size");
 }
 header('Content-Length: '.($end-$start+1));$f=fopen($path,'rb');fseek($f,$start);$left=$end-$start+1;
 while($left>0&&!feof($f)){ $chunk=fread($f,min(1048576,$left));echo $chunk;$left-=strlen($chunk);if(connection_aborted())break; }fclose($f);exit;
}
function archiveUpload(string $folder,array $allowed,int $limit): void{
 $f=$_FILES['archive']??null;if(!$f||$f['error']!==UPLOAD_ERR_OK)fail('Çıktı arşivi yüklenemedi.',422);
 $z=new ZipArchive();if($z->open($f['tmp_name'])!==true)fail('Geçersiz ZIP.',422);
 $total=0;
 for($i=0;$i<$z->numFiles;$i++){$st=$z->statIndex($i);if(!in_array($st['name'],$allowed,true))fail('Beklenmeyen arşiv dosyası.',422);$total+=$st['size'];if($total>$limit)fail('Arşiv sınırı aşıldı.',413);}
 if(!is_dir($folder))mkdir($folder,0700,true);
 foreach($allowed as $name){$stream=$z->getStream($name);if(!$stream)fail('Arşiv dosyası eksik: '.$name,422);$out=fopen($folder.'/'.$name.'.tmp','wb');stream_copy_to_stream($stream,$out);fclose($stream);fclose($out);rename($folder.'/'.$name.'.tmp',$folder.'/'.$name);}
 $z->close();
}
$path=parse_url($_SERVER['REQUEST_URI'],PHP_URL_PATH);$path=preg_replace('#^/api#','',$path);$method=$_SERVER['REQUEST_METHOD'];
$origin=$_SERVER['HTTP_ORIGIN']??'';
if($method!=='GET'&&$origin!==''&&$origin!==$config['origin'])fail('Kaynak adresine izin verilmiyor.',403);
$authorization=$_SERVER['HTTP_AUTHORIZATION']??$_SERVER['REDIRECT_HTTP_AUTHORIZATION']??'';
$worker=str_starts_with($authorization,'Bearer ')&&hash_equals($config['worker_hash'],hash('sha256',substr($authorization,7)));
if(!$worker){
 session_name('reels_session');session_set_cookie_params(['lifetime'=>0,'path'=>'/','secure'=>str_starts_with($config['origin'],'https://'),'httponly'=>true,'samesite'=>'Strict']);session_start();
}
$authenticated=$worker||($_SESSION['owner']??false);
try{
 if($path==='/health')reply(['mode'=>'cloud','authenticated'=>$authenticated,'ffmpeg'=>true,'ffprobe'=>true,'alignment'=>true,'models'=>['base','small'],'worker_online'=>(time()-(int)(meta('worker_seen')??'0'))<45,'version'=>'1.1.0']);
 if($path==='/auth/login'&&$method==='POST'){
  $key=hash('sha256',($_SERVER['REMOTE_ADDR']??'unknown').$config['worker_hash']);$attempt=q('SELECT * FROM reels_login_attempts WHERE id=?',[$key])->fetch();
  if($attempt&&time()-(int)$attempt['window_start']<300&&(int)$attempt['attempts']>=10)fail('Çok fazla deneme. Beş dakika sonra tekrar deneyin.',429);
  $password=body()['password']??'';if(!is_string($password)||strlen($password)>512)fail('Geçersiz parola.',401);
  if(!password_verify($password,$config['password_hash'])){
   if(!$attempt||time()-(int)$attempt['window_start']>=300){q('DELETE FROM reels_login_attempts WHERE id=?',[$key]);q('INSERT INTO reels_login_attempts VALUES(?,?,?)',[$key,1,time()]);}else q('UPDATE reels_login_attempts SET attempts=attempts+1 WHERE id=?',[$key]);
   fail('Parola doğru değil.',401);
  }
  q('DELETE FROM reels_login_attempts WHERE id=?',[$key]);session_regenerate_id(true);$_SESSION['owner']=true;reply(['ok'=>true]);
 }
 if($path==='/auth/logout'&&$method==='POST'){$_SESSION=[];session_destroy();reply(['ok'=>true]);}
 if(preg_match('#^/fonts/(serif|sans|mono)$#D',$path,$m))fileResponse(dirname(__DIR__).'/fonts/'.$m[1].'.ttf','font/ttf');
 if(!$authenticated)fail('Stüdyoya giriş yapın.',401);
 if(!$worker&&session_status()===PHP_SESSION_ACTIVE)session_write_close();
 if(str_starts_with($path,'/worker/')){
  if(!$worker)fail('Video motoru anahtarı geçersiz.',403);
  meta('worker_seen',(string)time());
  if($path==='/worker/claim'&&$method==='POST'){
   q("UPDATE reels_jobs SET status='queued',lease=NULL,message='Motor bağlantısı kesildi; yeniden sırada.' WHERE status='running' AND heartbeat<?",[time()-120]);
   $db->beginTransaction();$r=q("SELECT * FROM reels_jobs WHERE status='queued' AND cancelled=0 ORDER BY CASE kind WHEN 'ingest' THEN 0 WHEN 'scene' THEN 1 ELSE 2 END,created_at LIMIT 1")->fetch();
   if(!$r){$db->commit();reply(['job'=>null]);}
   $lease=uid();$changed=q("UPDATE reels_jobs SET status='running',lease=?,heartbeat=?,message='İşlem başlıyor…' WHERE id=? AND status='queued'",[$lease,time(),$r['id']])->rowCount();$db->commit();
   if(!$changed)reply(['job'=>null]);
   reply(['job'=>array_merge(jobRecord(getJob($r['id'])),['lease'=>$lease,'payload'=>json_decode($r['payload'],true),'project'=>project($r['project_id'])])]);
  }
  if(preg_match('#^/worker/jobs/([a-f0-9]{32})/(progress|complete|fail)$#D',$path,$m)&&$method==='POST'){
   $r=getJob($m[1]);$input=isset($_POST['result'])?json_decode($_POST['result'],true):body();
   if(!hash_equals($r['lease']??'',(string)($input['lease']??''))||$r['status']!=='running')fail('İşlem başka bir motora geçti.',409);
   if($r['cancelled']){q("UPDATE reels_jobs SET status='cancelled',message='İptal edildi.' WHERE id=?",[$r['id']]);reply(['cancel'=>true]);}
   if($m[2]==='progress'){q('UPDATE reels_jobs SET progress=?,message=?,heartbeat=? WHERE id=?',[max(0,min(1,(float)($input['progress']??$r['progress']))),mb_substr((string)($input['message']??$r['message']),0,500),time(),$r['id']]);reply(['cancel'=>false]);}
   if($m[2]==='fail'){q("UPDATE reels_jobs SET status='failed',message=? WHERE id=?",[mb_substr((string)($input['message']??'İşlem başarısız.'),0,1000),$r['id']]);reply(['ok'=>true]);}
   $p=project($r['project_id']);$payload=json_decode($r['payload'],true);$result=$input['data']??[];
   if($r['kind']==='ingest'){
    if(!is_numeric($result['audio']['duration']??null)||$result['audio']['duration']<.2||$result['audio']['duration']>600)fail('Ses süresi geçersiz.',422);
    $p['audio']=array_merge($p['audio'],$result['audio']);$p['audio']['file']=$payload['audio_file'];$result=saveProject($p);
   }elseif($r['kind']==='align'){
    $p['sentences']=$result['sentences'];$p['text']=$result['text'];$p['alignment']=$result['alignment'];validateEdit($p,$p);$result=saveProject($p);
   }elseif($r['kind']==='scene'){
    if(!preg_match('/^[a-f0-9]{20}$/D',$result['digest']??'')||count($result['sprites']??[])>180)fail('Geçersiz sahne.',422);
    $allowed=['background.jpg'];foreach($result['sprites'] as $i=>$sprite){if($sprite['file']!==$i.'.png')fail('Geçersiz görsel.',422);$allowed[]=$sprite['file'];}
    $dir=dirFor($p['id']).'/scenes/'.$result['digest'];archiveUpload($dir,$allowed,32*1024*1024);
    file_put_contents(dirFor($p['id']).'/scene-'.$payload['request_key'].'.json',enc($result),LOCK_EX);
   }elseif($r['kind']==='export'){
    $dir=dirFor($p['id']).'/exports/'.$r['id'];archiveUpload($dir,['video.mp4','subtitles.srt','timing.json'],128*1024*1024);
    $result=['files'=>[]];foreach(['video.mp4','subtitles.srt','timing.json'] as $name)$result['files'][$name]='/api/projects/'.$p['id'].'/exports/'.$r['id'].'/'.$name;
   }
   q("UPDATE reels_jobs SET status='completed',result=?,progress=1,message='Tamamlandı.' WHERE id=?",[enc($result),$r['id']]);reply(['ok'=>true]);
  }
  fail('İşlem bulunamadı.',404);
 }
 if($path==='/projects'&&$method==='GET'){$items=[];foreach(q('SELECT document FROM reels_projects ORDER BY updated_at DESC') as $r){$p=json_decode($r['document'],true);$items[]=['id'=>$p['id'],'name'=>$p['name'],'duration'=>$p['audio']['duration'],'updated_at'=>$p['updated_at']];}reply($items);}
 if($path==='/projects'&&$method==='POST'){
  $f=$_FILES['file']??null;if(!$f||$f['error']!==UPLOAD_ERR_OK)fail('Ses yüklenemedi. Dosya 100 MB sınırında olmalı.',422);
  $ext=strtolower(pathinfo($f['name'],PATHINFO_EXTENSION));if(!in_array($ext,['mp3','wav'],true)||$f['size']>100*1024*1024)fail('En fazla 100 MB MP3/WAV yükleyin.',422);
  $mime=(new finfo(FILEINFO_MIME_TYPE))->file($f['tmp_name']);if(!in_array($mime,['audio/mpeg','audio/x-wav','audio/wav','audio/vnd.wave','application/octet-stream'],true))fail('Geçersiz ses dosyası.',422);
  $id=uid();mkdir(dirFor($id),0700,true);$filename='audio.'.$ext;if(!move_uploaded_file($f['tmp_name'],dirFor($id).'/'.$filename))fail('Dosya saklanamadı.',500);
  $style=json_decode(file_get_contents(dirname(__DIR__).'/default-style.json'),true);
  $p=['id'=>$id,'name'=>mb_substr(pathinfo($f['name'],PATHINFO_FILENAME),0,120),'text'=>'','sentences'=>[],'style'=>$style,'alignment'=>null,'updated_at'=>time(),'audio'=>['file'=>$filename,'filename'=>mb_substr(basename($f['name']),0,240),'duration'=>0,'sample_rate'=>0,'channels'=>0,'waveform'=>[]]];
  q('INSERT INTO reels_projects VALUES(?,?,?)',[$id,enc($p),time()]);enqueue($id,'ingest',['audio_file'=>$filename]);reply($p);
 }
 if($path==='/example/audio')fileResponse(dirname(__DIR__).'/example.mp3','audio/mpeg');
 if(preg_match('#^/projects/([a-f0-9]{32})(?:/(.*))?$#D',$path,$m)){
  $pid=$m[1];$p=project($pid);$action=$m[2]??'';
  if($action===''&&$method==='GET')reply($p);
  if($action===''&&$method==='PUT'){reply(saveProject(array_merge($p,validateEdit(body(),$p))));}
  if($action==='audio')fileResponse(dirFor($pid).'/'.$p['audio']['file'],str_ends_with($p['audio']['file'],'.mp3')?'audio/mpeg':'audio/wav');
  if($action==='jobs')reply(array_map('jobRecord',q("SELECT * FROM reels_jobs WHERE project_id=? AND status IN ('queued','running') AND kind<>'scene' ORDER BY created_at",[$pid])->fetchAll()));
  if($action==='align'&&$method==='POST'){$e=body();splitText((string)($e['text']??''),$e['mode']??'sentences');if(!in_array($e['model']??'base',['tiny','base','small','medium'],true)||!in_array($e['device']??'cpu',['cpu','cuda'],true))fail('Model seçimi geçersiz.',422);reply(enqueue($pid,'align',$e));}
  if($action==='manual'&&$method==='POST'){
   if($p['audio']['duration']<=0)fail('Önce ses analizini bekleyin.',422);$e=body();$parts=splitText((string)($e['text']??''),$e['mode']??'sentences');$weights=array_map(fn($s)=>count(preg_split('/\s+/u',$s)),$parts);$sum=array_sum($weights);$cursor=0;$sentences=[];
   foreach($parts as $i=>$part){$end=$cursor+$p['audio']['duration']*$weights[$i]/$sum;$sentences[]=['id'=>'s'.($i+1),'text'=>$part,'start'=>$cursor,'end'=>$end,'review'=>true,'reason'=>'Elle zamanlama taslağı; sesle hizalanmadı.','accent'=>false,'words'=>[]];$cursor=$end;}
   $p['sentences']=$sentences;$p['text']=clean($e['text']);$p['alignment']=['engine'=>'manual'];validateEdit($p,$p);reply(saveProject($p));
  }
  if($action==='scene'&&$method==='POST'){
   $e=validateEdit(body(),$p);$key=substr(hash('sha256',enc(['style'=>$e['style'],'text'=>array_map(fn($s)=>[$s['text'],$s['accent']??false],$e['sentences'])])),0,32);
   $cache=dirFor($pid).'/scene-'.$key.'.json';if(is_file($cache))reply(json_decode(file_get_contents($cache),true));
   foreach(q("SELECT * FROM reels_jobs WHERE project_id=? AND kind='scene' AND status IN ('queued','running')",[$pid]) as $j){if((json_decode($j['payload'],true)['request_key']??'')===$key)reply(['pending'=>true,'job'=>$j['id']]);}
   $j=enqueue($pid,'scene',array_merge($e,['request_key'=>$key]));reply(['pending'=>true,'job'=>$j['id']]);
  }
  if(preg_match('#^scenes/([a-f0-9]{20})/(background\.jpg|\d+\.png)$#D',$action,$a))fileResponse(dirFor($pid).'/scenes/'.$a[1].'/'.$a[2],str_ends_with($a[2],'.png')?'image/png':'image/jpeg');
  if($action==='export'&&$method==='POST'){$e=body();validateEdit($e,$p,true);if(!in_array($e['quality']??'final',['final','preview'],true))fail('Çıktı kalitesi geçersiz.',422);reply(enqueue($pid,'export',$e));}
  if($action==='exports'){$r=q("SELECT id,result FROM reels_jobs WHERE project_id=? AND kind='export' AND status='completed' ORDER BY created_at DESC",[$pid])->fetchAll();reply(array_map(fn($x)=>['id'=>$x['id'],...json_decode($x['result'],true)],$r));}
  if(preg_match('#^exports/([a-f0-9]{32})/(video\.mp4|timing\.json|subtitles\.srt)$#D',$action,$a)){ $j=getJob($a[1]);if($j['project_id']!==$pid||$j['status']!=='completed')fail('Çıktı hazır değil.',404);fileResponse(dirFor($pid).'/exports/'.$a[1].'/'.$a[2],match($a[2]){'video.mp4'=>'video/mp4','timing.json'=>'application/json',default=>'application/x-subrip'},downloadName((json_decode($j['payload'],true)['name']??$p['name']),(int)$j['created_at'],$a[1],$a[2])); }
 }
 if(preg_match('#^/jobs/([a-f0-9]{32})(/cancel)?$#D',$path,$m)){$r=getJob($m[1]);if(isset($m[2])&&$method==='POST'){q("UPDATE reels_jobs SET cancelled=1,status=CASE WHEN status='queued' THEN 'cancelled' ELSE status END WHERE id=?",[$m[1]]);reply(['ok'=>true]);}reply(jobRecord($r));}
 fail('Uç nokta bulunamadı.',404);
}catch(Throwable $e){if($db->inTransaction())$db->rollBack();error_log('Reels API: '.$e->getMessage());fail('Sunucu işlemi tamamlayamadı. Sunucu günlüğünü kontrol edin.',500);}
