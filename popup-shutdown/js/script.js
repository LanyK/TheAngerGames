
let timer = undefined;

function sleep(ms)
{
    return new Promise (resolve => setTimeout (resolve, ms));
}

function close_popup(elm)
{
    document.body.removeChild (elm.parentElement.parentElement);
}

function generate_popup(min_x, max_x, min_y, max_y, height=undefined, width=undefined)
{
    if (height == undefined)
    {
      height = Math.floor (Math.random () * 10) + 10;
    }
    if (width == undefined)
    {
      width =  height * ((Math.random () * 4/9)+ (14/9));
    }
    let x = Math.floor (Math.random () * (max_x-min_x)) + min_x;
    let y = Math.floor (Math.random () * (max_y-min_y)) + min_y;
    if (x + width >= 99)
      x = 99 - width;

    if (y + height >= 99)
      y = 99 - height;

    let popup = `
      <div class="popup" style=" top: ` + y + `%; left:` + x + `%; width: ` + width + `%;height: ` + height + `%;">
        <div class="popup_header">
          <div class="close" onmousedown="close_popup(this)">&#10005;
          </div>
        </div>
        <div class="container">
         Failed to start the Game. Please try again ...
        </div>
      </div>`;
    document.body.innerHTML += popup;
}

async function start_game()
{
    document.getElementById ("controll").hidden = true;
    let ws = new WebSocket("ws://127.0.0.1:5678/");
    let anger = 0;

    for (let i = 0; i < 10; i++)
    {
        generate_popup(40+i,40+i,40+i,40+i,9*1.5,16*1.5);
        await sleep(20);
    }
    let win = false;

    async function generate()
    {
      while (true)
      {
        generate_popup(0, 80, 0, 80);
        await sleep(Math.max(4000 - anger*4000, 100));
        if (win == true)
        {
          break;
        }
      }
    }

    async function check_win()
    {
      while (true)
      {
        popups = document.getElementsByClassName ("popup");
        if (popups.length == 0)
        {
          win = true;
          document.getElementById ("controll").hidden = false;
          document.getElementById ("controll").innerText = "U WIN! AGAIN?"
          break;
        }
        await sleep(400);
      }
    }

    ws.onmessage = function (event)
    {
      data = JSON.parse(event.data);
      anger = data["anger"];
      c = document.getElementById("angerbar").childNodes[1];
      c.style.width  = anger*100 +"%";
    }

    generate();
    check_win();
}

/*
ADDITIONAL DEBUG STUFF
*/
function cheat()
{
    popups = document.getElementsByClassName ("popup");
    for (let i = 0; i < popups.length; i++)
    {
        document.body.removeChild (popups[i])
    }
}
//
