# BeerCalculator
Searches all available beer combinations with specific attributes for the game [Beer Manufacture Simulator](https://store.steampowered.com/app/3809410/Beer_Manufacture_Simulator/)
Currently it has data from v1.0.1

This entire project was pretty much vibe-coded with DeepSeek, so there might be bugs and errors.
I'm not sure that I would keep this project up-to-date, and it's distributed As-Is.
___

## How to use it
- You would need [Python3](https://www.python.org/downloads/)
- Download **calculator.py** and **ingredients.json**
- Open CMD in the folder with those files
- Type `python calculator.py`

Console has user interface, so just follow instructions at this point.

___

## How did I make this
This section is for those who would like to keep updating the data, mostly.
#### For all of this to work you must set the game to the Russian language. simplifyJson.py was build for it.
1. Download this repository
2. Download [BepInEx v6.x](https://builds.bepinex.dev/projects/bepinex_be). In our case, version Unity.IL2CPP-win-x64
3. Download [CinematicUnityExplorer](https://github.com/originalnicodr/CinematicUnityExplorer). BepInEx version for IL2CPP
4. Install both - unzip BepInEx into the game's folder, and put CinematicUnityExplorer folder inside plugins
5. Run the game. It should display console window and first run might take a while, as BepInEx would have to download unity dll's
6. In the game open Log and C# console.
7. In the console put 
```
using System.Text;
using System.Globalization;
```
8. Then 
```
var objs = Resources.FindObjectsOfTypeAll<BeerSpace.ObjectToCollect>();
Log("[");
foreach(var o in objs)
{
    var styles = o.GetStyleCompatibilities();
    if(styles.Count == 0)
        continue;
    
    var sb = new StringBuilder();
    sb.Append("{\n");
    sb.Append($"  \"Name\": \"{o.GetRecipeDisplayName()}\",\n");
    sb.Append($"  \"Type\": \"{o.ObjectCategory:F}\",\n");
    sb.Append($"  \"PerfectTemp\": {o.PerfectTemperature.ToString(CultureInfo.InvariantCulture)},\n");
    
    // Styles
    sb.Append("  \"Styles\": {\n");
    foreach(var style in styles)
    {
        sb.Append($"    \"{style.BeerStyle.ToString("F")}\": {style.Compatibility.ToString(CultureInfo.InvariantCulture)},\n");
    }
    sb.Length -= 2; // Удаляем последнюю запятую и перенос строки
    sb.Append("\n  },\n");
    
    // Parameters
    sb.Append("  \"Parameters\": {\n");
    foreach (var p in o.GetParameters())
    {
        sb.Append($"    \"{p.ParameterType.ToString("F")}\": {p.value.ToString(CultureInfo.InvariantCulture)},\n");
    }
    sb.Length -= 2; // Удаляем последнюю запятую и перенос строки
    sb.Append("\n  }\n");
    
    sb.Append("},");
    
    Log(sb.ToString());
}
Log("]");
```
9. Open log file (Beer Manufacture Simulator\BepInEx\LogOutput.log) and copy resulting output. Remove `[Message:UnityExplorer]`
10. Save resulted data as ingredients.json into the simplify folder and run cmd **python simplifyJson.py**
11. It would create file **ingredients_merged_best.json**. Save it as **ingredients.json** next to the **calculator.py**
12. Done. You can rename winhttp.dll to winhttp.dll.bak, this way the game would keep both mod and plugin, but would not run them untill you change name back to dll.

As long as the developers won't change the fact that all ingredients have the same stats no matter the quality it should work.